#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (C) 2015 - 2018 Martin Kauss (yo@bishoph.org)

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""

import logging
import audioop
from . import prepare
import time
import io


class processor:
    def __init__(self, cfg, buffering, live=True):
        self.append = False
        self.cfg = cfg
        self.out = None
        if self.cfg.getoption("cmdlopt", "outfile") is not None:
            self.out = io.open(self.cfg.getoption("cmdlopt", "outfile"), "wb")
        self.buffering = buffering
        self.live = live
        self.timer = 0
        self.silence_timer = 0
        self.silence_buffer = []
        self.prepare = prepare.preparing(self.cfg)
        self.logger = self.cfg.getlogger().getlog()
        self.logger = logging.getLogger(__name__)

    def stop(self, message):
        self.logger.info(message)
        if self.out is not None:
            self.out.close()
        self.append = False
        self.silence_timer = 0
        if not self.cfg.getbool("cmdlopt", "endless_loop"):
            self.prepare.stop()
        else:
            self.prepare.force_tokenizer()
        if self.buffering is not None:
            self.buffering.stop()

    def check_silence(self, buf):
        volume = audioop.rms(buf, 2)
        if volume >= self.cfg.getintoption("stream", "THRESHOLD"):
            self.silence_timer = time.time()
            if not self.append:
                self.logger.info("starting append mode")
                self.timer = time.time()
                for sbuf in self.silence_buffer:
                    self.prepare.prepare(sbuf, audioop.rms(sbuf, 2))
                self.silence_buffer = []
            self.append = True
        else:
            self.silence_buffer.append(buf)
            if len(self.silence_buffer) > 3:
                del self.silence_buffer[0]
        if self.out is not None and not self.out.closed:
            self.out.write(buf)
        if self.append:
            self.prepare.prepare(buf, volume)
        if (
            self.append
            and self.silence_timer > 0
            and self.silence_timer
            + self.cfg.getfloatoption("stream", "MAX_SILENCE_AFTER_START")
            < time.time()
            and self.live
        ):
            self.stop("stop append mode because of silence")
        if (
            self.append
            and self.timer + self.cfg.getfloatoption("stream", "MAX_TIME") < time.time()
            and self.live
        ):
            self.stop("stop append mode because time is up")
