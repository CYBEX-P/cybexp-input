import json
import logging
import sys

import tahoe

# default config
default = {
    "mongo": { 
        "mongo_url": "mongodb://localhost:27017/",
        "identity_db": "identity_db"
        "identity_coll": "instance"
  },
    "api": {
        "url": "localhost:5000"
  }
}


def get_config():
    """Read config from file `config.json`."""
  
    try: 
        with open('config.json', 'r') as f:
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


def get_mongoconfig():
    """Configuration of Identity Backend."""
  
    config = get_config()
    mongoconfig = config['mongo']
    for k, v in default['mongo'].items():
        if k not in mongoconfig:
            mongoconfig[k] = v
    return mongoconfig
      

def get_apiconfig():
    """Configuration of API."""
    
    config = get_config()
    apiconfig = config['api']
    for k, v in default['api'].items():
        if k not in apiconfig:
            apiconfig[k] = v
    return apiconfig
        

def get_identity_backend():
    mongoconfig = get_mongoconfig()
    mongo_url = mongoconfig['mongo_url']
    dbname = mongoconfig['identity_db']
    collname = mongoconfig['identity_coll']
    backend = tahoe.identity.IdentityBackend(mongo_url, dbname, collname)
    return backend



























