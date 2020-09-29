import json
import logging
import os
import sys

import tahoe

# default config
default = {
    "mongo": { 
        "mongo_url": "mongodb://localhost:27017/",
        "identity_db": "identity_db",
        "identity_coll": "instance"
  },
    "api": {
        "url": "http://localhost:5000/raw",
        "token": ""
  }
}


def get_config(filename='config.json'):
    """
    Retrieves the general configuration provided by the passed file.
    If a cofiguration element is not available in the passed configuration file,
    that element is replaced by the corresponding value in the default dictionary.

    Parameters
    ----------
    filename: String
        name of the configuration file
        Default: 'config.json'

    Raises
    ------

    FileNotFoundError
        If no file is found, all configurations will default and raise a warning
    JSONDecodeError
        Improper configuration file, administrate a system exit

    Returns
    -------
    config: Dictionary
        A Dictionary of the configuration attributes

    """
  
    try:
        this_dir = os.path.dirname(__file__)
        filename = os.path.join(this_dir, filename)
        with open(filename, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = default
        logging.warning("No config file found, using default config")
    except json.decoder.JSONDecodeError:
        logging.error("Bad configuration file!", exc_info=True)
        sys.exit(1) # 1 = error in linux

    for k, v in default.items():
        if k not in config:
            config[k] = v

    return config


def get_mongoconfig(filename='config.json'):
    """
    Utility function. Retrieves the mongodb configuration from the passed file.
    If a value of a configuration is missing in the passed configuration file,
    that element is replaced by the corresponding value in the default dictionary.
    
    Parameters
    ----------
    filename: String
        name of the configuration file
        Default: 'config.json'
    
    Returns
    -------
    mongoconfig: Dictionary
        A Dictionary of the configuration attributes

    """
  
    config = get_config(filename)
    mongoconfig = config['mongo']
    for k, v in default['mongo'].items():
        if k not in mongoconfig:
            mongoconfig[k] = v
    return mongoconfig
      

def get_apiconfig(filename='config.json'):
    """
    Retrieves the API configuration from the passed json configuration file.
    If a value of a configuration is missing in the passed configuration file,
    that element is replaced by the corresponding value in the default dictionary.

    Parameters
    ----------
    filename: String
        name of the configuration file
        Default: 'config.json'
    
    Returns
    -------
    apiconfig: Dicionary
        A Dictionary of the configuration attributes

    """
    
    config = get_config(filename)
    apiconfig = config['api']
    
    for k, v in default['api'].items():
        if k not in apiconfig:
            apiconfig[k] = v
    return apiconfig
        

def get_identity_backend(filename='config.json'):
    """
    Retrieves the full backend configuration from the passed json configuration file.
    calls the get_mongoconfig function and stores the return list of configuration attributes into variable 'mongoconfig'.
    stores the URL, identity database, and identity collection in seperate variabes and passed them into a tahoe identity_backend
    class call. that object is stored into a 'backend' variable and returned.

    Parameters
    ----------
    filename: String
        name of the configuration file
        Default: 'config.json'
    
    Returns
    -------
    backend: Class     
        Identity backend object


    """
    mongoconfig = get_mongoconfig(filename)
    mongo_url = mongoconfig['mongo_url']
    dbname = mongoconfig['identity_db']
    collname = mongoconfig['identity_coll']
    backend = tahoe.identity.IdentityBackend(mongo_url, dbname, collname)
    return backend



























