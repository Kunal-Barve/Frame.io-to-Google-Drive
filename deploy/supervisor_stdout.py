#!/usr/bin/env python
# This script helps supervisor forward process stdout/stderr to the container's stdout/stderr
# so logs are properly captured by Cloud Run logging

import sys

def write_stdout(s):
    sys.stdout.write(s)
    sys.stdout.flush()

def write_stderr(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def event_handler(event, response):
    if event['eventname'] == 'PROCESS_LOG':
        if event['data']['channel'] == 'stdout':
            write_stdout(event['data']['data'])
        else:
            write_stderr(event['data']['data'])
    response.write("OK")
    response.flush()

def main():
    while True:
        try:
            header_line = sys.stdin.readline()
            if not header_line:
                break
            headers = dict([x.split(':') for x in header_line.split()])
            data = sys.stdin.read(int(headers['len']))
            event = dict([x.split(':') for x in data.split()])
            response = sys.stdout
            event_handler(event, response)
        except KeyboardInterrupt:
            break
        except:
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()