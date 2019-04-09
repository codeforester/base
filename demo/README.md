# Logging demo

``` bash
2019-04-09:14:08:04 DEBUG   ./logging_demo.sh:31 This is a debug log
2019-04-09:14:08:04 INFO    ./logging_demo.sh:32 This is an info log
2019-04-09:14:08:04 WARN    ./logging_demo.sh:33 This is a warning
2019-04-09:14:08:04 ERROR   ./logging_demo.sh:34 This is an error
2019-04-09:14:08:04 FATAL   ./logging_demo.sh:35 This is a fatal error
2019-04-09:14:08:04 VERBOSE ./logging_demo.sh:38 This is a verbose log
2019-04-09:14:08:04 WARN    ./logging_demo.sh:44 This is a warning
2019-04-09:14:08:04 INFO    ./logging_demo.sh:10 Entering function test_func
2019-04-09:14:08:04 DEBUG   ./logging_demo.sh:11 Entering function test_func
2019-04-09:14:08:04 VERBOSE ./logging_demo.sh:12 Entering function test_func
2019-04-09:14:08:04 INFO    ./logging_demo.sh:14 Leaving function test_func
2019-04-09:14:08:04 DEBUG   ./logging_demo.sh:15 Leaving function test_func
2019-04-09:14:08:04 VERBOSE ./logging_demo.sh:16 Leaving function test_func
2019-04-09:14:08:04 DEBUG   ../lib/stdlib.sh:161 Contents of file '/tmp/__log_demo__.txt':
first line
second line
third line
2019-04-09:14:08:04 DEBUG   ../lib/stdlib.sh:161 Contents of file '/tmp/__log_demo__.txt':
first line
second line
third line
2019-04-09:14:08:04 DEBUG   ../lib/stdlib.sh:161 Contents of file '/tmp/__log_demo__.txt':
first line
second line
third line
ERROR: This is a plain error
WARN: This is a plain warning
This is a plain info
```
# Error handling demo

```bash
2019-04-09:14:07:33 DEBUG   ./error_handling_demo.sh:10 Entering function test_func1
2019-04-09:14:07:33 INFO    ./error_handling_demo.sh:11 Calling test_func2
2019-04-09:14:07:33 DEBUG   ./error_handling_demo.sh:18 Entering function test_func2
2019-04-09:14:07:33 INFO    ./error_handling_demo.sh:19 Calling test_func3
2019-04-09:14:07:33 DEBUG   ./error_handling_demo.sh:26 Entering function test_func3
2019-04-09:14:07:33 DEBUG   ./error_handling_demo.sh:21 Leaving function test_func2
2019-04-09:14:07:33 FATAL   ../lib/stdlib.sh:240 test_func2 failed
Encountered a fatal error
     at exit_if_error (../lib/stdlib.sh:241)
     at test_func1 (./error_handling_demo.sh:13)
     at main (./error_handling_demo.sh:34)
     at main (./error_handling_demo.sh:38)
2019-04-09:14:07:33 DEBUG   ./error_handling_demo_lib.sh:6 Entering function demo_lib_func
2019-04-09:14:07:33 FATAL   ../lib/stdlib.sh:240 Deliberately exiting!
Encountered a fatal error
     at exit_if_error (../lib/stdlib.sh:241)
     at demo_lib_func (./error_handling_demo_lib.sh:7)
     at main (./error_handling_demo.sh:35)
     at main (./error_handling_demo.sh:38)
```
