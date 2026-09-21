// Copyright 2026 Gautham Anil
// SPDX-License-Identifier: Apache-2.0
// Isolated coco.v1 transport candidate; no UI imports or automatic robot commands.
export const STREAMS = Object.freeze(
  ['telemetry', 'mission', 'lidar', 'map', 'path', 'camera', 'depth']);
export const DEFAULT_STREAMS = Object.freeze(STREAMS.slice(0, 5));
const integer = (v, min = 0, max = Number.MAX_SAFE_INTEGER) =>
  Number.isSafeInteger(v) && v >= min && v <= max;
const finite = v => typeof v === 'number' && Number.isFinite(v);
function requireValue(ok, message) { if (!ok) throw new Error(message); }

export function decodeFrame(buffer) {
  requireValue(buffer instanceof ArrayBuffer, 'expected ArrayBuffer');
  requireValue(buffer.byteLength >= 8, 'short frame');
  const view = new DataView(buffer);
  requireValue(view.getUint32(0) === 0x434f434f && view.getUint8(4) === 1,
    'unknown frame format');
  const stream = {1: 'lidar', 2: 'camera', 3: 'depth'}[view.getUint8(5)];
  requireValue(stream, 'unknown stream');
  const length = view.getUint16(6), end = 8 + length;
  requireValue(length <= 8192 && end <= buffer.byteLength, 'invalid header length');
  const header = JSON.parse(new TextDecoder('utf-8', {fatal: true})
    .decode(new Uint8Array(buffer, 8, length)));
  requireValue(header && typeof header === 'object' && !Array.isArray(header),
    'invalid header');
  const payload = new Uint8Array(buffer, end), size = payload.byteLength;
  requireValue(size <= 8 * 1024 * 1024, 'payload too large');
  requireValue(header.stream === stream && integer(header.seq) &&
    finite(header.t) && header.t >= 0 && integer(header.dropped ?? 0),
  'invalid common metadata');
  requireValue(!['topic', 'service', 'message_type', 'target']
    .some(key => Object.hasOwn(header, key)), 'ROS target in sensor metadata');
  if (Object.hasOwn(header, 'payload_bytes')) {
    requireValue(integer(header.payload_bytes, 0, 8 * 1024 * 1024) &&
      header.payload_bytes === size, 'payload size mismatch');
  }
  let ranges;
  if (stream === 'lidar') {
    requireValue(integer(header.count, 0, 4 * 1024 * 1024) &&
      header.count * 2 === size, 'ray count mismatch');
    requireValue(finite(header.angle_min) && finite(header.angle_step) &&
      header.scale === 1000 && header.no_return === 0 &&
      (header.enc ?? 'uint16be-mm') === 'uint16be-mm' &&
      (header.floor == null || (finite(header.floor) && header.floor >= 0)),
    'invalid lidar metadata');
    // DataView handles unaligned JSON-header endings and network byte order.
    const rays = new DataView(buffer, end, size);
    ranges = Array.from({length: header.count}, (_, i) => {
      const mm = rays.getUint16(i * 2);
      return mm === 0 ? null : mm / header.scale;
    });
  } else {
    requireValue(integer(header.w, 1, 8192) && integer(header.h, 1, 8192) &&
      header.w * header.h <= 8 * 1024 * 1024 && header.enc === 'jpeg',
    'invalid image metadata');
    if (Object.hasOwn(header, 'quality'))
      requireValue(integer(header.quality, 1, 100), 'invalid quality');
    if (stream === 'depth')
      requireValue(finite(header.min_m) && finite(header.max_m) &&
        0 <= header.min_m && header.min_m < header.max_m, 'invalid depth range');
    if (!Object.hasOwn(header, 'payload_bytes'))
      requireValue(payload[0] === 255 && payload[1] === 216 &&
        payload[size - 2] === 255 && payload[size - 1] === 217,
      'truncated legacy JPEG');
  }
  return {stream, header, payload, ...(ranges ? {ranges} : {})};
}

function validateStreams(names) {
  requireValue(Array.isArray(names) && names.every(n => STREAMS.includes(n)),
    'unknown stream');
  return names;
}

export class Transport {
  constructor(url, {WebSocketImpl = globalThis.WebSocket,
    schedule = setTimeout, cancel = clearTimeout, now = Date.now,
    onFrame = () => {}, onState = () => {}, onError = () => {},
    heartbeatMs = 10000, timeoutMs = 10000} = {}) {
    Object.assign(this, {url, WebSocketImpl, schedule, cancel, now,
      onFrame, onState, onError, heartbeatMs, timeoutMs});
    this.desired = new Set(DEFAULT_STREAMS);
    this.state = 'DISCONNECTED';
    this.timers = new Set();
    this.stopped = true;
    this.attempt = 0;
    this.socket = null;
    this.awaitingPong = null;
  }
  later(fn, delay) {
    const id = this.schedule(() => { this.timers.delete(id); fn(); }, delay);
    this.timers.add(id);
    return id;
  }
  clearTimers() {
    for (const id of this.timers) this.cancel(id);
    this.timers.clear();
    this.awaitingPong = null;
  }
  setState(state) { this.state = state; this.onState(state); }
  connect() {
    if (!this.stopped) return;
    this.stopped = false;
    this.open();
  }
  open() {
    if (this.stopped) return;
    this.setState('CONNECTING');
    const socket = new this.WebSocketImpl(this.url);
    this.socket = socket;
    socket.binaryType = 'arraybuffer';
    const current = () => this.socket === socket && !this.stopped;
    socket.onopen = () => {
      if (!current()) return;
      this.setState('CONNECTED');
      this.attempt = 0;
      this.send({type: 'hello', protocol: 'coco.v1', binary: true});
      const add = [...this.desired].filter(s => !DEFAULT_STREAMS.includes(s));
      const remove = DEFAULT_STREAMS.filter(s => !this.desired.has(s));
      if (add.length) this.send({type: 'subscribe', streams: add});
      if (remove.length) this.send({type: 'unsubscribe', streams: remove});
      this.later(() => this.heartbeat(), this.heartbeatMs);
    };
    socket.onmessage = event => {
      if (!current()) return;
      try {
        const frame = typeof event.data === 'string'
          ? JSON.parse(event.data) : decodeFrame(event.data);
        if (frame.type === 'pong' && frame.t === this.awaitingPong) {
          this.awaitingPong = null;
          this.cancel(this.deadline);
          this.timers.delete(this.deadline);
        }
        // Frames already in flight before unsubscribe may still arrive.
        if (!frame.stream || this.desired.has(frame.stream)) this.onFrame(frame);
      } catch (error) { this.onError(error); }
    };
    socket.onerror = () => { if (current()) socket.close(); };
    socket.onclose = () => {
      if (!current()) return;
      this.socket = null;
      this.clearTimers();
      this.setState('RECONNECTING');
      this.later(() => this.open(), Math.min(30000, 1000 * 2 ** this.attempt++));
    };
  }
  heartbeat() {
    if (this.state !== 'CONNECTED') return;
    if (this.awaitingPong === null) {
      this.awaitingPong = this.now();
      this.send({type: 'ping', t: this.awaitingPong});
      this.deadline = this.later(() => {
        if (this.awaitingPong !== null) this.socket?.close();
      }, this.timeoutMs);
    }
    this.later(() => this.heartbeat(), this.heartbeatMs);
  }
  send(frame) {
    requireValue(this.state === 'CONNECTED' && this.socket?.readyState === 1,
      'not connected');
    this.socket.send(JSON.stringify(frame));
  }
  subscribe(names) {
    validateStreams(names);
    for (const name of names) this.desired.add(name);
    if (this.state === 'CONNECTED')
      this.send({type: 'subscribe', streams: [...new Set(names)]});
  }
  unsubscribe(names) {
    validateStreams(names);
    const removable = [...new Set(names)].filter(s => s !== 'telemetry');
    for (const name of removable) this.desired.delete(name);
    if (this.state === 'CONNECTED')
      this.send({type: 'unsubscribe', streams: removable});
  }
  close() {
    this.stopped = true;
    this.clearTimers();
    const socket = this.socket;
    this.socket = null;
    socket?.close();
    this.setState('DISCONNECTED');
  }
}
