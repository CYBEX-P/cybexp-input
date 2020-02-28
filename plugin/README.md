# Plugin Requirement

`def inputCheck(args)` must be defined. this functions checks wheter a dictionary has the correct configuration to create `InputPlugin`. Must return `True` or `False`.   

The main plugin must be a class named `InputPlugin` and must inherit from `CybexSource`.

# Helpful

use `self.backoffExit.is_set()` to check whether is has gracefully request to end, this is a request, please process all the data that to avoid loss. Use this as an outter loop check


use `self.exit_signal.is_set()` to check whether is you are reesueted to end as coon as possible. Please leave/release the thread ASAP, data could be lost. Please include this in most places, as inner loop checks. You might still have time to save some data, but if you get this you mig get a SIGKILL and yyou get no choice, so do it fast. 

# Helper functions 

`CybexSource.exit()`  will request to exit after data is process. Will set `self.backoffExit`.   

`CybexSource.exit_NOW()`  will request to exit ASAP. Will set `self.exit_signal`.   
