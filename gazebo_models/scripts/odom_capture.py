#!/usr/bin/env python3
"""Opt-in acquisition-stamped GT sidecar; pure Python, no ROS initialization."""
import atexit
import json
import queue
import threading


class GroundTruthCapture:
    """Bounded nonblocking producer; disk I/O belongs to the worker only."""

    def __init__(self, path, capacity=4096):
        self.file = open(path, 'x', encoding='utf-8')
        self.queue = queue.Queue(capacity)
        self.dropped = 0
        self.successful = 0
        self.malformed = 0
        self.failed = None
        self.epoch = 0
        self.last_receipt = None
        self.sequence = 0
        self.closed = False
        self.stop = threading.Event()
        self.file.write(json.dumps({'schema': 1, 'stage': 'manifest',
                                   'kind': 'ground_truth'}) + '\n')
        self.worker = threading.Thread(target=self._drain, daemon=True)
        self.worker.start()
        atexit.register(self.close)

    def add(self, message, receipt_sim, receipt_wall):
        if self.closed:
            return
        if self.last_receipt is not None and receipt_sim < self.last_receipt:
            self.epoch += 1
        self.last_receipt = receipt_sim
        self.sequence += 1
        stamp = message.header.stamp
        p, q = message.pose.pose.position, message.pose.pose.orientation
        record = {'schema': 1, 'stage': 'gt', 'id': self.sequence,
                  'epoch': self.epoch,
                  'stamp_ns': stamp.sec * 1_000_000_000 + stamp.nanosec,
                  'receipt_sim': receipt_sim, 'receipt_wall': receipt_wall,
                  'frame': message.header.frame_id,
                  'child': message.child_frame_id,
                  'pose': [p.x, p.y, p.z, q.x, q.y, q.z, q.w]}
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            self.dropped += 1

    def _drain(self):
        try:
            while not self.stop.is_set() or not self.queue.empty():
                try:
                    record = self.queue.get(timeout=0.02)
                except queue.Empty:
                    continue
                try:
                    encoded = json.dumps(record, allow_nan=False)
                except (ValueError, TypeError):
                    self.malformed += 1
                    continue
                self.file.write(encoded + '\n')
                self.file.flush()
                self.successful += 1
        except (OSError, ValueError) as error:
            self.failed = str(error)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.stop.set()
        self.worker.join()
        try:
            footer = {'schema': 1, 'stage': 'footer', 'dropped': self.dropped,
                      'write_failed': self.failed is not None,
                      'error': self.failed, 'attempted': self.sequence,
                      'successful': self.successful, 'malformed': self.malformed,
                      'completion': ('complete' if not self.failed and not self.dropped
                                     and not self.malformed and
                                     self.sequence == self.successful else 'incomplete')}
            self.file.write(json.dumps(footer) + '\n')
        finally:
            self.file.close()
