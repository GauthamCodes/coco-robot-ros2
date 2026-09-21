// Copyright 2026 Gautham Anil
// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeFrame, Transport} from './client.mjs';

const fixtures = JSON.parse(readFileSync(process.env.COCO_FRAME_FIXTURES, 'utf8'));
const arrayBuffer = encoded => Uint8Array.from(Buffer.from(encoded, 'base64')).buffer;
test('Python sensor encoders decode in JavaScript, including network byte order', () => {
  for (const [stream, blob] of Object.entries(fixtures.valid)) {
    const result = decodeFrame(arrayBuffer(blob));
    assert.equal(result.stream, stream);
    assert.equal(result.header.seq, 7);
    assert.equal(result.header.t, 12.5);
    if (stream === 'lidar') assert.deepEqual(result.ranges, [1.234, null, 2]);
    else assert.equal(result.header.w, 8);
  }
});
test('Python malformed fixtures are refused by the browser decoder', () => {
  for (const blob of fixtures.invalid) assert.throws(() => decodeFrame(arrayBuffer(blob)));
});

class FakeSocket {
  static instances = [];
  constructor() { this.readyState = 0; this.sent = []; FakeSocket.instances.push(this); }
  open() { this.readyState = 1; this.onopen?.(); }
  send(value) { this.sent.push(JSON.parse(value)); }
  message(value) { this.onmessage?.({data: JSON.stringify(value)}); }
  close() { this.readyState = 3; this.onclose?.(); }
}
function fixture() {
  const tasks = new Map();
  let id = 0;
  const options = {
    WebSocketImpl: FakeSocket, now: () => 42,
    schedule: (fn, delay) => { tasks.set(++id, {fn, delay}); return id; },
    cancel: id => tasks.delete(id),
  };
  const transport = new Transport('ws://fixture', options);
  const runDelay = delay => {
    const [key, task] = [...tasks].find(([, t]) => t.delay === delay);
    tasks.delete(key); task.fn();
  };
  return {transport, tasks, runDelay};
}

test('reconnect restores stream choices and never replays drive', () => {
  const {transport, tasks, runDelay} = fixture();
  transport.subscribe(['camera', 'camera']);
  transport.unsubscribe(['path']);
  transport.connect();
  const first = FakeSocket.instances.at(-1);
  first.open();
  assert.deepEqual(first.sent.map(f => f.type), ['hello', 'subscribe', 'unsubscribe']);
  transport.send({type: 'drive', linear: 0.1});
  first.close();
  assert.equal(transport.state, 'RECONNECTING');
  assert.throws(() => transport.send({type: 'drive'}));
  runDelay(1000);
  const second = FakeSocket.instances.at(-1);
  second.open();
  assert.deepEqual(second.sent.map(f => f.type), ['hello', 'subscribe', 'unsubscribe']);
  assert.deepEqual(second.sent[1].streams, ['camera']);
  assert.deepEqual(second.sent[2].streams, ['path']);
  transport.close();
  assert.equal(tasks.size, 0);
});

test('old sockets cannot alter a new connection and intentional close stays closed', () => {
  const {transport, tasks, runDelay} = fixture();
  transport.connect();
  const old = FakeSocket.instances.at(-1);
  old.open(); old.close(); runDelay(1000);
  FakeSocket.instances.at(-1).open();
  old.onclose(); old.onopen();
  assert.equal(transport.state, 'CONNECTED');
  transport.close();
  assert.equal(transport.state, 'DISCONNECTED');
  assert.equal(tasks.size, 0);
});

test('heartbeat pong cancels the deadline and missing pong reconnects', () => {
  const {transport, tasks, runDelay} = fixture();
  transport.connect();
  const socket = FakeSocket.instances.at(-1);
  socket.open(); runDelay(10000);
  assert.equal(socket.sent.at(-1).type, 'ping');
  socket.message({type: 'pong', t: 42});
  assert.equal(tasks.size, 1);
  runDelay(10000); // next heartbeat, no pong
  runDelay(10000); // deadline closes socket
  assert.equal(transport.state, 'RECONNECTING');
  assert.equal(tasks.size, 1);
  transport.close();
});

test('invalid subscription is atomic and telemetry remains enabled', () => {
  const {transport} = fixture();
  const before = [...transport.desired];
  assert.throws(() => transport.subscribe(['camera', '/raw']));
  assert.deepEqual([...transport.desired], before);
  transport.unsubscribe(['telemetry']);
  assert(transport.desired.has('telemetry'));
});
