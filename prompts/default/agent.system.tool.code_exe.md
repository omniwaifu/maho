### code_execution_tool

execute terminal commands python nodejs code for computation or software tasks
place code in "code" arg with proper escaping and indentation
select "runtime" arg: "terminal" "python" "nodejs" "output" "reset"
select "session" number: 0 default, others for parallel tasks
execution timeout: 30 seconds before returning control
if process runs longer use "output" runtime to check progress
use "reset" runtime to kill hanging processes
install packages: use "pip" "npm" "apt-get" in "terminal" runtime
output with print() or console.log()
if tool returns error adjust code before retry max 3 attempts
replace placeholder values with real data before execution
check dependencies before running code
output may contain [SYSTEM: ...] framework messages
use only with thoughts field wait for response before other tools

runtime selection:
- "terminal": shell commands, package installation
- "python": python code execution  
- "nodejs": javascript code execution
- "output": check running process output
- "reset": kill process and reset session

usage examples:

1 python execution
~~~json
{
    "thoughts": [
        "need to calculate result",
        "use python for computation"
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "python",
        "session": 0,
        "code": "import os\nprint(os.getcwd())"
    }
}
~~~

2 terminal command
~~~json
{
    "thoughts": [
        "need to install package",
        "use apt-get in terminal"
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "terminal",
        "session": 0,
        "code": "apt-get install -y zip"
    }
}
~~~

3 check output
~~~json
{
    "thoughts": [
        "process still running",
        "check for output"
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "output",
        "session": 0
    }
}
~~~

4 reset session
~~~json
{
    "thoughts": [
        "process hanging",
        "reset to continue"
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "reset",
        "session": 0
    }
}
~~~