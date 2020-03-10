#!/usr/bin/env python3 

import pymongo
import json 
import importlib
import logging
import hashlib
import sys

def hash_string(hash_string): # TODO, make deterministic
   sha_signature = hashlib.sha512(hash_string.encode()).hexdigest()
   return sha_signature


class InputDB():
   def __init__(self, URL="mongodb://localhost:27017", DBName="InputDB", configColl="configs",
                  pluginConfCol="plugin_configs", logger=logging.getLogger("InputDBLogger")):
      self.client = pymongo.MongoClient(URL)
      self.db = self.client[DBName]
      self.confCol = self.db[configColl]
      self.confCol.create_index("hash", unique=True)
      self.confCol.create_index("input_plugin_name")

      # define plugin coll
      self.pluginsCol = self.db[pluginConfCol]
      self.pluginsCol.create_index("input_plugin_name", unique=True)
      self.pluginsCol.create_index("enabled")


      self.logger = logger

   def insert_config(self, human_name,input_plugin_name, archive_processing_typetag,
                     orgid, plugin_type="scheduled",
                     timezone="UTC",enabled=False, **kwargs):
      args = locals()
      args.pop("self")
      args_kw = args.pop("kwargs")
      args.update(args_kw)

      # todo make this into function, check everywhere
      if plugin_type == "scheduled":
         if "seconds_between_fetches" not in args:
            return False
      elif plugin_type == "service":
         pass
      elif plugin_type == "manual_sync":
         pass
      else:
         return False

      try:
         pluginName = "plugin.{}".format(input_plugin_name)
         plugin = importlib.import_module(pluginName)
         check = plugin.inputCheck(args)
         del plugin
         if not check:
            return False
      except ModuleNotFoundError:
         self.logger.info("Failed to import module")
         return False

      # check = plugins.get(plugin).check(args)
      # if not check:
      #    return False
      config = { "human_name": human_name, 
                  "input_plugin_name":  input_plugin_name,
                  "archive_processing_typetag":  archive_processing_typetag,
                  "timezone":  timezone,
                  "orgid":  orgid,
                  # "all": args
      }
      # config.update(kwargs)
      # print(config)
      args["hash"] = hash_string(str(args))
      args["enabled"] = enabled
      try:
         x = self.confCol.insert_one(args)
      except pymongo.errors.DuplicateKeyError:
         print("duplicate key")
         return False
      # print(x)
      return x.inserted_id

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
         print(r)

   def update_one(self,coll, query, update:dict):
      if coll == self.confCol: # if a config item rehash
         config_type = True
         print("its a config")
      else:
         print("its a pluginconfig")
         config_type = False      
      # query = { "hash": conf_hash }
      if len(query) > 1: # only one key allowed
         return False
      record = coll.find_one(query,{"_id":0,"hash":0})
      # print("query:",query)
      # print("record:\t\t",record)
      # print("update:",update)
      if record == None:
         return False

      record.update(update)
      # print("new record:\t",record)

      if "enabled" not in record:
         record["enabled"] = False

      enabled = record.pop("enabled")

      if config_type:
         record["prev_hash"] = record["hash"]
         newHash = hash_string(str(record))
         record["hash"] = newHash

      record["enabled"] = enabled
      print("record:\t\t",record)


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
         print("Failed to import module")
         # print("Unexpected error:", sys.exc_info()[0])
         return False

      newvalues = { "$set": record }
      try:
         coll.update_one(query, newvalues)
         return True
      except pymongo.errors.DuplicateKeyError:
         print("New or modified record already exists. cant modify")
         return False

   def update_config(self,conf_hash, update:dict):
      return self.update_one(self.confCol, { "hash": conf_hash } , update)

   def enable_disable_conf(self, conf_hash, enabled:bool):
      return self.update_config(conf_hash , {"enabled": enabled})

   def disableConfig(self, conf_hash):
      return self.enable_disable_conf(conf_hash, False)
   def enableConfig(self, conf_hash):
      return self.enable_disable_conf(conf_hash, True)

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
         print("duplicate key")
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
      temp.append(query)
      masterQ = { "$and": temp }

      return self.getConfig(masterQ, select)


   def notifyStream(self, resume = False):
      if resume and self.resumeToken:
         self.changeStreamCursor = self.confCol.watch([], {
         resumeAfter: resumeToken,
         # fullDocument: "updateLookup"
        })
        # print("\r\nResuming change stream with token " + JSON.stringify(resumeToken) + "\r\n");
        # resumeStream(newChangeStreamCursor)
      # self.changeStreamCursor.close()
      while not self.changeStreamCursor.isExhausted():
         if self.changeStreamCursor.hasNext():
            change = self.changeStreamCursor.next()
            print(change)
            self.resumeToken = change._id
            
               
         
       




   def notifyChanges(self):
   # https://www.mongodb.com/blog/post/an-introduction-to-change-streams
   # https://docs.mongodb.com/manual/tutorial/deploy-replica-set/
   # https://docs.mongodb.com/manual/reference/method/db.collection.watch/#db.collection.watch
   # https://docs.mongodb.com/manual/changeStreams/#open-a-change-stream # main info 
   # 
      # print("hi")
      self.changeStreamCursor = self.confCol.watch()
   #    # try:
   #    self.notifyStream()
   # # except:
      # self.notifyStream(True)

   # function resumeStream(changeStreamCursor, forceResume = false) {
   #   let resumeToken;
   #   while (!changeStreamCursor.isExhausted()) {
   #     if (changeStreamCursor.hasNext()) {
   #       change = changeStreamCursor.next();
   #       print(JSON.stringify(change));
   #       resumeToken = change._id;
   #       if (forceResume === true) {
   #         print("\r\nSimulating app failure for 10 seconds...");
   #         sleepFor(10000);
   #         changeStreamCursor.close();
   #         const newChangeStreamCursor = collection.watch([], {
   #           resumeAfter: resumeToken
   #         });
   #         print("\r\nResuming change stream with token " + JSON.stringify(resumeToken) + "\r\n");
   #         resumeStream(newChangeStreamCursor);
   #       }
   #     }
   #   }
   #   resumeStream(changeStreamCursor, forceResume);
   # }



if __name__ == "__main__":
   a = InputDB()
   a.notifyChanges()

   # a.insert_config(**{ "human_name": "abc1", 
   #                   "input_plugin_name": "phishtank" ,
   #                   "archive_processing_typetag": "processing1" ,
   #                   "timezone": "UTC" ,
   #                   "orgid": "random stuff" ,
   #                   "testtag1": "Highway 1" ,
   #                   "testtag2": "Highway 2" ,
   #                })

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
   # ac = a.addPlugin("amazing 2","phishtank",True)
   # ad = a.addPlugin("amazing 3","misp_file",False)

   # print(ab,ac,ad)
   # bb = a.enablePlugin("misp_file")
   # print(bb)
   # cc = a.disablePlugin("misp_file")
   # print(cc)

   pass