#!/usr/bin/env python3 

import pymongo
import json 
import importlib
import logging
#import hashlib
import sys
import uuid

# def hash_string(hash_string): # TODO, make deterministic
#    sha_signature = hashlib.sha512(hash_string.encode()).hexdigest()
#    return sha_signature


DEFAULT_MONGO = "mongodb://192.168.1.101:30001,192.168.1.101:30002,192.168.1.101:30003/?replicaSet=rs0"

class InputDB():
   def __init__(self, URL=DEFAULT_MONGO, DBName="InputDB",
                  configColl="configs",
                  pluginConfCol="plugin_configs",
                  pluginInstanceCol="plugin_instance",
                  logger=logging.getLogger("InputDBLogger")):

      self.client = pymongo.MongoClient(URL)
      self.db = self.client[DBName]
      self.confCol = self.db[configColl]
      self.confCol.create_index("uuid", unique=True)
      self.confCol.create_index("input_plugin_name")

      # define plugin coll
      self.pluginsCol = self.db[pluginConfCol]
      self.pluginsCol.create_index("input_plugin_name", unique=True)
      self.pluginsCol.create_index("enabled")

      self.pInstanceCol = self.db[pluginInstanceCol]
      self.pInstanceCol.create_index("uuid", unique=True)


      self.logger = logger

   def insert_config(self, human_name,input_plugin_name, archive_processing_typetag,
                     orgid, #plugin_type="scheduled",
                     timezone="UTC",enabled=False, **kwargs):
      args = locals()
      args.pop("self")
      args_kw = args.pop("kwargs")
      args.update(args_kw)
      print("test2")
      # # todo make this into function, check everywhere
      # if plugin_type == "scheduled":
      #    if "seconds_between_fetches" not in args:
      #       return False
      # elif plugin_type == "service":
      #    pass
      # elif plugin_type == "manual_sync":
      #    pass
      # else:
      #    return False

      try:
         pluginName = "plugin.{}".format(input_plugin_name)
         plugin = importlib.import_module(pluginName)
         check = plugin.inputCheck(args)
         del plugin
         # print("check:",check)
         if not check:
            return False
      except ModuleNotFoundError:
         self.logger.info("Failed to import module")
         return False
      # print("test3")

      config = { "human_name": human_name, 
                  "input_plugin_name":  input_plugin_name,
                  "archive_processing_typetag":  archive_processing_typetag,
                  "timezone":  timezone,
                  "orgid":  orgid,
                  # "all": args
      }
      # config.update(kwargs)
      # print(config)
      args["uuid"] = str(uuid.uuid4()) #hash_string(str(args))
      args["enabled"] = enabled
      try:
         # print(args)
         x = self.confCol.insert_one(args)
      except pymongo.errors.DuplicateKeyError:
         # print("duplicate key")
         return False
      # print(x)
      return args["uuid"] #x.inserted_id

   def getConfig(self, query={},select={ "_id": 0 }):
      return self.confCol.find(query,select)
   def getPlugins(self, query={},select={ "_id": 0 }):
      return self.pluginsCol.find(query,select)

   def import_bulk_config(self, fileName):
      with open(fileName) as json_file:
         try:
            data = json.load(json_file)
         except:
            return
      for entry in data:
         r = self.insert_config(**entry)
         # print(r)

   def update_one(self,coll, query, update:dict):
      if coll == self.confCol: 
         config_type = True
         # print("its a config")
      elif coll == self.confCol: 
         module_type = True
         # print("its a config")
      else:
         # print("its not config type")
         config_type = False 
         module_type = False

     
      # query = { "hash": conf_hash }
      if len(query) > 1: # only one key allowed
         return False
      record = coll.find_one(query,{"_id":0})
      # print("query:",query)
      # print("record:\t\t",record)
      # print("update:",update)
      if record == None:
         return False

      record.update(update)
      # print("new record:\t",record)

      

      if config_type or module_type:
         if "enabled" not in record:
            record["enabled"] = False

         enabled = record.pop("enabled")


         record["enabled"] = enabled
         # print("record:\t\t",record)

         try:
            input_plugin_name = record["input_plugin_name"]
            pluginName = "plugin.{}".format(input_plugin_name)
            # print(pluginName)
            plugin = importlib.import_module(pluginName)
            if config_type: # only check if we are updating a plugin configuration
               check = plugin.inputCheck(record)
               if not check:
                  return False
            del plugin

         except ModuleNotFoundError:
            # print("Failed to import module")
            # print("Unexpected error:", sys.exc_info()[0])
            # TODO logger 
            return False

      newvalues = { "$set": record }
      try:
         coll.update_one(query, newvalues)
         return True
      except pymongo.errors.DuplicateKeyError:
         # print("New or modified record already exists. cant modify")
         return False

   def update_config(self,conf_uuid, update:dict):
      return self.update_one(self.confCol, { "uuid": conf_uuid } , update)

   def enable_disable_conf(self, conf_uuid, enabled:bool):
      return self.update_config(conf_uuid , {"enabled": enabled})

   def disableConfig(self, conf_uuid):
      return self.enable_disable_conf(conf_uuid, False)
   def enableConfig(self, conf_uuid):
      return self.enable_disable_conf(conf_uuid, True)

   def addPlugin(self,human_name, input_plugin_name, enabled=False):

      try:
         pluginName = "plugin.{}".format(input_plugin_name)
         plugin = importlib.import_module(pluginName)
         if not callable(plugin.inputCheck):
            self.logger.info("Failed to import module {}. Does not contain inputcheck() function.".format(input_plugin_name))
            return False
         del plugin
      except ModuleNotFoundError:
         self.logger.info("Failed to import module {}. Does not contain inputcheck() function.".format(input_plugin_name))
         return False

      record = { "human_name": human_name, 
                  "input_plugin_name":  input_plugin_name,
                  "enabled":  enabled
      }
      try:
         x = self.pluginsCol.insert_one(record)
      except pymongo.errors.DuplicateKeyError:
         # print("duplicate key")
         return False
      # print(x)
      return x.inserted_id

   def removePlugin():
      pass
   def enable_disable_plugin(self, input_plugin_name, enabled:bool):
      return self.update_one(self.pluginsCol,{"input_plugin_name": input_plugin_name} , {"enabled": enabled})

   def disablePlugin(self, input_plugin_name):
      return self.enable_disable_plugin(input_plugin_name, False)
   def enablePlugin(self, input_plugin_name):
      return self.enable_disable_plugin(input_plugin_name, True)


   def getValidPlugins(self):
      plugins = self.getPlugins(query={"enabled": True},select={"_id":0,"input_plugin_name":1})
      valid = list()
      for record in plugins:
         valid.append(record["input_plugin_name"])
      return valid
      # valid = [plug["input_plugin_name"] for plug in plugins]
      # print("Valid:",valid)
      # return valid


   def getValidConfig(self, query={}, select={"_id": 0}): # TODO fix not checking if config is valid
      temp = list()
      valid = self.getValidPlugins()

      temp.append({"input_plugin_name": { "$in": valid}})
      temp.append({"enabled": True})
      temp.append(query)
      masterQ = { "$and": temp }

      return self.getConfig(masterQ, select)




   def changeHandler(self, funcChangehandler, **kwargs):
      resume_token = None
      critical = False
      while not critical:
         try:
            # pipeline = [{'$match': {'operationType': 'insert'}},
            # {'$match': {
            #         'operationType': {'$in': ['insert', 'replace']}
            #     }},
            #     {'$match': {
            #         'newDocument.n': {'$gte': 1}
            #     }}]
            if resume_token:
               with self.confCol.watch(full_document="updateLookup",
                   resume_after=resume_token) as stream:
                  for change in stream:
                     funcChangehandler(change)
            else:
               with self.confCol.watch(full_document="updateLookup") as stream:
                  for change in stream:
                     # print(change)
                     # print(change["fullDocument"])
                     allowed_ops = ['insert', 'delete', 'replace', 'update' ]
                     if change["operationType"] in allowed_ops:
                        funcChangehandler(change, **kwargs)
                        
                     resume_token = stream.resume_token

         except pymongo.errors.PyMongoError:
            print("pymongo error")
             # The ChangeStream encountered an unrecoverable error or the
             # resume attempt failed to recreate the cursor.
            if resume_token is None:
                 # There is no usable resume token because there was a
                 # failure during ChangeStream initialization.
               logging.critical('...')
               critical = True
            else:
               pass
                 # Use the interrupted ChangeStream's resume token to create
                 # a new ChangeStream. The new stream will continue from the
                 # last seen insert change without missing any events.

# DEFAULT_MONGO = "mongodb://192.168.1.101:30001,192.168.1.101:30002,192.168.1.101:30003/?replicaSet=rs0"

# client = pymongo.MongoClient(DEFAULT_MONGO)
# db = client["InputDB"]
# confCol = db["configs"]

# change_stream = confCol.watch()
# for change in change_stream:
#     print(change)
#     # print(json.dumps(change))
#     print('') # for readability only




# thre will be a new colloectin, so the watch stream wont trigger when chanign these
   def createPID(self, conf_uuid:str, pid:int):
      data = {"uuid":conf_uuid, "pid": pid}
      try:
         x = self.pInstanceCol.insert_one(data)
      except pymongo.errors.DuplicateKeyError:
         print("duplicate key")
         return False
      return x.inserted_id

   def getPID(self,conf_uuid:str):
      query={"uuid":conf_uuid}
      select={ "_id": 0 }
      record = self.pInstanceCol.find_one(query,select)
      if record:
         return record["pid"]
      else:
         return 0
   def updatePID(self,conf_uuid:str, pid:int):
      return self.update_one(self.pInstanceCol, {"uuid": conf_uuid}, {"pid": pid})

   def setPID(self, conf_uuid:str, pid:int):
      if self.getPID(conf_uuid):
         return self.updatePID(conf_uuid, pid)
      else:
         return self.createPID(conf_uuid, pid)


if __name__ == "__main__":
   a = InputDB()
   # a.notifyChanges()
   print("test")
   a.insert_config(**{ "human_name": "abc1", 
                     "input_plugin_name": "phishtank" ,
                     "archive_processing_typetag": "processing1" ,
                     "timezone": "UTC" ,
                     "orgid": "random stuff" ,
                     "enabled": True,
                     "testtag1": "Highway 1" ,
                     "testtag2": "Highway 2" ,
                     'seconds_between_fetches': 5
                  })

   # a.import_bulk_config("config2.json")
   # h = "70453c868caa749141b461a28feca64d41363e46ff97cf6a7f9b916ac83c8ad725459f725b597a1f198849072289c8e18281e058a7f64e45d9110e3b92b3923e"
   # a.update_config(h ,{"new_value":"test"})
   # # a.insert_config(**{ "human_name": "abc2", 
   #                   "input_plugin_name": "openphish" ,
   #                   "archive_processing_typetag": "processing2" ,
   #                   "timezone": "UTC" ,
   #                   "orgid": "random stuff" ,
   #                   "testtag1": "Highway 1" ,
   #                   "testtag2": "Highway 2" ,

   #                })
   # a.insert_config(**{ "human_name": "abc3", 
   #                   "input_plugin_name": "openphish" ,
   #                   "archive_processing_typetag": "processing3" ,
   #                   "timezone": "UTC" ,
   #                   "orgid": "random stuff" ,
   #                   "testtag1": "Highway 1" ,
   #                   "testtag2": "Highway 2" ,

   #                })
   # a.insert_config(**{ "human_name": "abc4", 
   #                   "input_plugin_name": "openphish" ,
   #                   "archive_processing_typetag": "processing4" ,
   #                   "timezone": "UTC" ,
   #                   "orgid": "random stuff" ,
   #                   "testtag1": "Highway 1" ,
   #                   "testtag2": "Highway 2" ,

   #                })

   # print([item for item in a.getAll()])
   # for item in a.getAll():
   #    print(item)
   # ab = a.addPlugin("amazing name","test",True)
   ac = a.addPlugin("amazing 2","phishtank",True)
   # ad = a.addPlugin("amazing 3","misp_file",False)

   # print(ab,ac,ad)
   # bb = a.enablePlugin("misp_file")
   # print(bb)
   # cc = a.disablePlugin("misp_file")
   # print(cc)

   pass


# TODO 
# replace print for logging 
