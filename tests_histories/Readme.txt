A) Reconstructed javascript code added: "Main.info"
Output of the json_printer. It was called by me with the following parameters out of its directory:
 ./bin/syntree/main --num_data_records=1 --data=/home/pa/Desktop/Repository/ProgramAnalysisProject/tests_histories/programs.json -log_dir=/home/pa/Desktop/Repository/ProgramAnalysisProject/tests_histories

The log information are actually annoying and the format is wrong.
For parsing one has to remove first 3 lines and remove then all lines containing the prefix I0510.
Additionally to make js_call_graph read the file, I had to give the function a name "TEST" and to add brackets arround the functions for a proper immediate execution.
http://stackoverflow.com/questions/6719089/javascript-anonymous-function-immediate-invocation-execution-expression-vs-dec

The preprocessing has been done manually for this first test and the isolated code has been stored as "IsolatedCode.js"



B) Call graph added:
This was created by running js_call_graph on the reconstructed preprocessed javascript file "IsolatedCode.js".
The ouput has been stored under "callgraph"



=> Now all necessary data should be available to give it a try in histories.py

