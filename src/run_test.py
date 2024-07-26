""" This code to connect OpenText API """
import argparse
import base64
import logging
import sys
import time
import xml.etree.ElementTree as ET
 
import requests
 
import constant
 
# Parameters from AWS Codebuild
buildvariable_parser = argparse.ArgumentParser()
buildvariable_parser.add_argument("lr_user_name", type=str,
                                  help="microfocus username")
buildvariable_parser.add_argument("lr_password", type=str,
                                  help="microfocus password")
buildvariable_parser.add_argument("lr_domain_name", type=str,
                                  help="microfocus domain_name")
buildvariable_parser.add_argument("lr_project_name", type=str,
                                  help="microfocus project_name")
buildvariable_parser.add_argument("lr_scenario_test_id", type=int,
                                  help="microfocus scenario test id")
buildvariable_parser.add_argument("lr_scenario_test_instance_id", type=int,
                                  help="microfocus scenario test instance id")
buildvariable_parser.add_argument("logging_level", type=str,
                                  help="logging level")
args = buildvariable_parser.parse_args()
 
 
logging = logging.getLogger(__name__)
logging.setLevel(level=args.logging_level)
 
def main():
    """main function to call the microfocus api requests in sequence to authenticate credentials,
     start the test,get run id, get the initial run status, get periodical run status and
     get final run status/run sla status and finally validate sla status for pass/fail/error """
 
    print("Username ",args.lr_user_name)
    print("Password ", args.lr_password)
    print("Domain Name ", args.lr_domain_name)
    print("ProjectName ", args.lr_project_name)
    print("test_id ", args.lr_scenario_test_id)
    print("Instance_id ", args.lr_scenario_test_instance_id)
    print("logginLevel ", args.logging_level)
 
    auth_api_header = b64_encode_credentials()
    auth_response_cookies = mf_authenticate_req(auth_api_header)
    api_headers = create_req_headers(auth_response_cookies)
    run_id = start_run(api_headers)
    get_run_status_resp = get_run_status_req(api_headers, run_id)
    initial_run_state = get_run_status_resp_value(get_run_status_resp)
    periodic_run_status(api_headers, run_id, initial_run_state)
 
 
def b64_encode_credentials():
    """Encode Credentials and return Authorization header"""
    encoded_credentials = (str(base64.b64encode(f"{args.lr_user_name}:"
                                                f"{args.lr_password}".encode(constant.UTF)),
                               constant.UTF))
    print("encoded_credentials ", encoded_credentials)
    return {'Authorization': f"Basic {encoded_credentials}"}
 
 
def mf_authenticate_req(auth_api_header):
    """Trigger Authenticate API request and return response cookies """
    mf_authenticate_api = f"{constant.MF_URL}{constant.REQ_AUTHENTICATE}"
    return (requests.get(mf_authenticate_api, headers=auth_api_header)).cookies.get_dict()
 
 
def create_req_headers(auth_response_cookies):
    """Capture the required response cookies from auth response
    and append content type to create api header"""
    lwsso_value = auth_response_cookies['LWSSO_COOKIE_KEY']
    qcsesion_value = auth_response_cookies['QCSession']
    return {'Content-Type': "application/xml",
            'Cookie': f"LWSSO_COOKIE_KEY={lwsso_value};QCSession={qcsesion_value};"}
 
 
def start_run(api_headers):
    """Start the Test Run - API request
    Trigger call to microfocus to start the test and return the runid"""
    start_run_api_url = f"{constant.MF_URL}{constant.MF_LOAD_API}" \
                        f"{args.lr_domain_name}/projects/{args.lr_project_name}/Runs"
    start_run_api_payload = f"<Run xmlns=\"http://www.hp.com/PC/REST/API\">" \
                            f"<PostRunAction>Collate And Analyze</PostRunAction>" \
                            f"<TestID>{args.lr_scenario_test_id}</TestID>" \
                            f"<TestInstanceID>{args.lr_scenario_test_instance_id}" \
                            f"</TestInstanceID>" \
                            f"<TimeslotDuration>" \
                            f"<Hours>1</Hours>" \
                            f"<Minutes>30</Minutes>" \
                            f"</TimeslotDuration><VudsMode>false</VudsMode></Run>"
    start_run_response_formatted = ET.fromstring((requests.post(start_run_api_url,
                                                                data=start_run_api_payload,
                                                                headers=api_headers)).text)
    # Extract RUN ID from start_run_full_response
    for child in start_run_response_formatted:
        if child.tag == constant.RUN_ID:
            test_run_id = child.text
            logging.info("Test started and the Run ID is %s", test_run_id)
            return test_run_id
        if child.tag == constant.ERROR:
            error_message = child.text
            logging.info("unable to start the test due to %s", error_message)
            return error_message
    raise RuntimeError("Run id not returned, please check the run in microfocus")
 
 
def get_run_status_req(api_headers, run_id):
    """Get Run Status - API request
    get the run status of the current run using the runid """
    get_run_status_api_url = f"{constant.MF_URL}{constant.MF_LOAD_API}" \
                             f"{args.lr_domain_name}/projects/{args.lr_project_name}/" \
                             f"Runs/{run_id}"
    return ET.fromstring((requests.get(get_run_status_api_url, headers=api_headers)).text)
 
 
def get_run_status_resp_value(get_run_status_response_formatted):
    """Extract RUN Status from get_run_status_response"""
    for child in get_run_status_response_formatted:
        if child.tag == constant.RUN_STATUS:
            run_state = child.text
            return run_state
    raise RuntimeError("Unable to get the status, please check the run in microfocus")
 
 
def get_run_sla_status_value(get_run_status_response_formatted):
    """Extract RUN Status from get_run_status_response"""
    for child in get_run_status_response_formatted:
        if child.tag == constant.RUN_SLA_STATUS:
            run_sla_state = child.text
            return run_sla_state
    raise RuntimeError("Unable to get the status, please check the run in microfocus")
 
 
def periodic_run_status(api_headers, run_id, run_state):
    """Run the loop every 30 sec to check the test status"""
    logging.debug("Test started and the initial Run status %s", run_state)
    while run_state not in ['Run Failure', 'Failed Collating Results',
                            'Failed Creating Analysis Data', 'Canceled',
                            'Finished']:
        logging.debug("Waiting for %d secs", constant.DELAY_TIMER)
        time.sleep(constant.DELAY_TIMER)
        run_state = get_run_status_resp_value(get_run_status_req(api_headers, run_id))
        logging.debug("Run status after delay of %d sec, %s", constant.DELAY_TIMER, run_state)
 
    run_sla_status = get_run_sla_status_value(get_run_status_req(api_headers, run_id))
    logging.debug("Test run sla status is %s", run_sla_status)
 
    if run_sla_status == 'Passed':
        logging.info('Test passed')
        sys.exit(0)
    else:
        logging.info('Test Failed')
        sys.exit("Test Execution Failed as run SLA Status not Met")
 
 
if __name__ == "__main__":
    main()
