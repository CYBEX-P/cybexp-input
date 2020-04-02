import logging 
import logging.handlers
import sys
import json

exformatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")



class TlsSMTPHandler(logging.handlers.SMTPHandler):
   def emit(self, record):
      try:
         import smtplib
         try:
            from email.utils import formatdate
         except ImportError:
            formatdate = self.date_time
         port = self.mailport
         if not port:
            port = smtplib.SMTP_PORT
         smtp = smtplib.SMTP(self.mailhost, port)
         msg = self.format(record)
         msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\nDate: %s\r\n\r\n%s" % (
                        self.fromaddr,
                        ",".join(self.toaddrs),
                        self.getSubject(record),
                        formatdate(), msg)
         if self.username:
            smtp.ehlo() # for tls add this line
            smtp.starttls() # for tls add this line
            smtp.ehlo() # for tls add this line
            smtp.login(self.username, self.password)
         smtp.sendmail(self.fromaddr, self.toaddrs, msg)
         smtp.quit()
      except (KeyboardInterrupt, SystemExit):
         raise
      except:
         self.handleError(record)



def setLoggerLevel(loggerName="InputLogger",level=logging.DEBUG):
   logger = logging.getLogger(loggerName)
   logger.setLevel(level)


def setup_file(loggerName="InputLogger",level=logging.INFO,formatter=exformatter,fileLoc:str='archive.log'):
   logger = logging.getLogger(loggerName)
   # logger = logging.root
   fh = logging.FileHandler(fileLoc)
   fh.setLevel(level)  
   fh.setFormatter(formatter)
   logger.addHandler(fh)

def setup_email(server, port, loggerName="InputLogger",formatter=exformatter, level=logging.DEBUG,from_email='ignaciochg@gmail.com', to=['ignaciochg@nevada.unr.edu'], subject='Error found!',cred=('ignaciochg@gmail.com', 'qadytrsyudzkdidu')):

   logger = logging.getLogger(loggerName)
   # logger = logging.root
   if cred:
      gm = TlsSMTPHandler((server, port), from_email, to, subject, cred)
   else:
      gm = TlsSMTPHandler((server, port), from_email, to, subject)
   gm.setLevel(level)
   gm.setFormatter(formatter)
   logger.addHandler(gm)

def setup_email(conf_file, loggerName="InputLogger",formatter=exformatter, level=logging.DEBUG, subject=None):
   with open(filename) as f:
      try:
         config = json.load(f)
      except json.decoder.JSONDecodeError:
         print("Bad email config file {}. Exiting...".format(filename))
         sys.exit(1)
   
   if "port" in config:
      host = (config["server"], config["port"]) 
   else:
      host = config["server"]
   if not subject:
      subject = config["subject"]
   if "username" in config and "password" in config:
      cred = (config["username"], config["password"])
   else:
      cred = None


   logger = logging.getLogger(loggerName)
   # logger = logging.root
   if cred:
      gm = TlsSMTPHandler(host, config["from"], config["to"], subject, cred)
   else:
      gm = TlsSMTPHandler(host, config["from"], config["to"], subject)
   
   gm.setLevel(level)
   gm.setFormatter(formatter)
   logger.addHandler(gm)

def setup_stdout(loggerName="InputLogger",level=logging.DEBUG,formatter=exformatter):
   logger = logging.getLogger(loggerName)
   # logger = logging.root
   stdouth = logging.StreamHandler(sys.stdout)
   stdouth.setLevel(level)  
   stdouth.setFormatter(formatter)
   logger.addHandler(stdouth)

if __name__ == "__main__":
   setLoggerLevel()
   setup_stdout(formatter=exformatter)
   setup_file(formatter=exformatter)
   setup_email(formatter=exformatter)
   # logger.debug('debug message')
   # logger.info('info message')
   # logger.warning('warn message')
   # logger.error('error message')
   # logger.critical('critical message')
