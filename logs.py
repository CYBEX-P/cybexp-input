import logging 
import logging.handlers

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


def setup_file(loggerName="InputLogger",level=logging.INFO,formatter=exformatter,fileLoc='archive.log'):
   logger = logging.getLogger(loggerName)
   # logger = logging.root
   fh = logging.FileHandler(fileLoc)
   fh.setLevel(level)  
   fh.setFormatter(formatter)
   logger.addHandler(fh)

def setup_email(loggerName="InputLogger",formatter=exformatter, level=logging.DEBUG,from_email='ignaciochg@gmail.com', to=['ignaciochg@nevada.unr.edu'], subject='Error found!',cred=('ignaciochg@gmail.com', 'qadytrsyudzkdidu')):

   logger = logging.getLogger(loggerName)
   # logger = logging.root
   gm = TlsSMTPHandler(("smtp.gmail.com", 587), from_email, to,subject , cred)
   gm.setLevel(level)
   gm.setFormatter(formatter)
   logger.addHandler(gm)




if __name__ == "__main__":
   setLoggerLevel()
   setup_file(formatter=exformatter)
   setup_email(formatter=exformatter)
   # logger.debug('debug message')
   # logger.info('info message')
   # logger.warning('warn message')
   # logger.error('error message')
   # logger.critical('critical message')
