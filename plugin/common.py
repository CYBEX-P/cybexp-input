# Imports
import datetime, json, logging, random, requests, threading, time, uuid, signal

loggerName = "InputLogger"

def inputCheck(args):
    return False


class BadConfig(Exception):
    pass


def exponential_backoff(n, threadEvent=None, name=None):
    logger = logging.getLogger(loggerName)

    s = min(3600, (2 ** n) + (random.randint(0, 1000) / 1000))
    resume_time = (datetime.datetime.now() + datetime.timedelta(seconds=s)).strftime(
        "%I:%M:%S %p"
    )
    logger.error(f"Sleeping for {s} seconds, will resume around {resume_time}.")
    if threadEvent:
        threadEvent.clear() # set to false
        requested_to_exit = threadEvent.wait(s) #  wait  or exit on set
        if not name:
            name = "backoff"
        if requested_to_exit:
            logger.info(
            f"{name}-- early exiting backoff."
            )
    else: 
        time.sleep(s)


class CybexSource:
    timezone = "UTC"

    def __init__(self, api_config, input_config):
        self.logger = logging.getLogger(loggerName)
        self.exit_signal = threading.Event()
        self.backoffExit = threading.Event()

        self.logger.info(
            "Configuring {} with ".format(input_config["human_name"])+
            "type = {} ".format(input_config['input_plugin_name'])+
            "orgid = {} ".format(input_config['orgid'])+
            "typtag = {} ".format(input_config['archive_processing_typetag'])+
            "timezone = {} ".format(input_config['timezone'])
        )

        # Should extract orgid, typtag, timezone from input_config.json
        for config_element, config_value in input_config.items():
            setattr(self, config_element, config_value)

        def validate_input_config():
            """ Validate configuration for this specific Cybex vuln. source. """
            if ("orgid", "archive_processing_typetag") - input_config.keys():
                raise BadConfig("Config needs an Org ID and a type tag.")

            try:
                uuid.UUID(self.orgid)
            except ValueError:
                raise BadConfig(f"Config needs a valid UUID, got {self.orgid}")

        validate_input_config()

        self.post_url = api_config["url"] + "/api/v1.0/raw"
        self.token = api_config["token"]

    def __str__(self):
        return "Cybexp Input, api server = {}, post url = {}".format(
            self.api_srv, self.post_url
        )

    def fetch_and_post(self):
        """ Fetch vulnerability data from this Cybex source. """
        raise NotImplementedError

    def post_event_to_cybex_api(self, events):
        """ Post an event from the Cybex source to the Cybex API. """
        if type(events) != list:
            events = [events]
        api_responses = []

        if events:
            self.logger.info(f"Posting {len(events)} events from {self.human_name} to Cybex API.")

        for event in events:
            if isinstance(event, dict):
                event = json.dumps(event)
            data = event.encode()
            files = {"file": data}
            headers = {"Authorization": "Bearer " + self.token}
            
            n_failed_requests = 0
            while not self.exit_signal.is_set():
                try:
                    with requests.post(
                        self.post_url,
                        files=files,
                        headers=headers,
                        data={
                            "orgid": self.orgid,
                            "typtag": self.archive_processing_typetag,
                            "timezone": self.timezone,
                            "name": self.human_name,
                        },
                    ) as r:
                        api_responses.append((r.status_code, r.content))

                        r.close()

                        if r.status_code >= 200 and r.status_code < 400:
                            n_failed_requests = 0
                            break
                        else:
                            self.logger.error(
                                f"Failed to post {self.human_name} to Cybex API:\n{r.text}"
                            )
                            n_failed_requests += 1
                except KeyboardInterrupt:
                    self.exit()

                except requests.exceptions.ConnectionError as e:
                    self.logger.exception(f"Failed to post {self.human_name} to Cybex API")
                    n_failed_requests += 1

                # print(n_failed_requests)
                exponential_backoff(n_failed_requests,self.backoffExit, "plugin.{}.post_event_to_cybex_api".format(self.input_plugin_name))

        return api_responses

    def exit(self):
        self.backoffExit.set()
        print("source")
    def exit_NOW(self):
        self.exit_signal.set()
        self.backoffExit.set()

class CybexSourceFetcher(threading.Thread):
    seconds_between_fetches = 10

    def __init__(self, cybex_source: CybexSource):
        super().__init__()
        self.exit_signal = threading.Event()
        self.backoffExit = threading.Event()
        self.logger = logging.getLogger(loggerName)

        self.source = cybex_source
        self.source_name = cybex_source.input_plugin_name

        if hasattr(cybex_source, "seconds_between_fetches"):
            self.seconds_between_fetches = cybex_source.seconds_between_fetches

        self.logger.info(
            f"plugin.{self.source_name}-- Applying rate limiting of {self.seconds_between_fetches} seconds between fetches"
        )

    def rate_limit(self, n_failed_queries):
        """ Can use more complicated limiting logic; sleep for now. """
        if n_failed_queries > 0:
            self.logger.warning(
                f"plugin.{self.source_name}-- backing off exponentially due to failures."
            )
            exponential_backoff(n_failed_queries, self.backoffExit, "plugin.{}".format(self.source_name))
        else:
            self.logger.info(
                f"plugin.{self.source_name}-- waiting for {self.seconds_between_fetches}."
            )

            self.backoffExit.clear() # set to false
            requested_to_exit = self.backoffExit.wait(self.seconds_between_fetches) #  wait  or exit on set
            if requested_to_exit:
                self.logger.info(
                f"plugin.{self.source_name}-- early exiting backoff."
                )
    def run(self):
        n_failed_queries = 0
        while not self.exit_signal.is_set():
            try:
                self.logger.info(
                    f"Fetching vulnerability information from {self.source_name}."
                )
                # In general, we expect fetch and post to be atomic operations
                # If fetching from the vuln. data source OR posting fails, then
                # the entire operation raises and we retry with backoff. In fact,
                # some threat data sources (HoneyPot) only send data once,
                # requiring caching to make retries meaningful. However, if
                # fetch_and_post is implemented non-atomically (drops read-once
                # data or can succeed even if data is partially reported), then
                # we may report data to the Cybex API out-of-order or incompletely
                try:
                    self.source.fetch_and_post()
                except KeyboardInterrupt:
                    self.exit()
                n_failed_queries = 0
            except KeyboardInterrupt:
                self.exit()
            except Exception:
                self.logger.error(f"plugin.{self.source_name}-- ", exc_info=True)
                n_failed_queries += 1

            if not self.exit_signal.is_set():
                self.rate_limit(n_failed_queries)

    def exit(self):
        self.logger.info("{}-- Handling exit.".format(self.source_name))
        self.exit_signal.set()
        self.backoffExit.set()
        self.source.exit()
        print("backoff exit:",self.backoffExit.is_set())
        print("exit:",self.exit_signal.is_set())
    def exit_NOW(self):
        self.logger.info("{}-- Handling exit.".format(self.source_name))
        self.exit_signal.set()
        self.backoffExit.set()
        self.source.exit_NOW()
        print("backoff exit:",self.backoffExit.is_set())
        print("exit:",self.exit_signal.is_set())

    def signal_handler(self,sig):
        print("##### start ##########")
        print(sig)
        if sig == signal.SIGTERM:
            print("will do")
            self.exit()
        if sig == signal.SIGINT:
            self.exit()
        if sig == signal.SIGKILL:
            print("OK i will kill myself")
            self.exit_NOW()
        else:
            self.exit()
        print("#####  end  ##########")



        