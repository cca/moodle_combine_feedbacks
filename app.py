import os

from dotenv import dotenv_values
from requests import get, HTTPError

# a tripartite set of API calls:
# 1. get all courses in the Internships category (may need to weed out demo/template courses)
# wsfunction: TBD
# 2. get all Feedback activities from courses (1 request, no need for iteration)
# wsfunction: mod_feedback_get_feedbacks_by_courses
# 3. iterate over feedbacks, get all their analyses
# wsfunction: mod_feedback_get_analysis

conf = {
    **dotenv_values(".env"),  # load private env
    **os.environ,  # override loaded values with environment variables
}

# 2: get feedbacks
service = 'mod_feedback_get_feedbacks_by_courses'
format = 'json'
params = {
    # see https://moodle.cca.edu/admin/settings.php?section=webservicetokens
    'wstoken': conf['TOKEN'],
    'wsfunction': service,
    'moodlewsrestformat': format,
    'courseids[]': 5204
}

response = get(conf['URL'], params=params)
print(response.url)
try:
    response.raise_for_status()
except HTTPError:
    print(f'HTTP Error {response.status_code}')
    print(response.headers)
    print(response.text)

data = response.json()
print(data)
feedbacks = data["feedbacks"]
# example feedback structure:
# {
#   "id": 1520,
#   "course": 5204,
#   "name": "Submit Employer and Intern Information",
#   "intro": "",
#   "introformat": 1,
#   "anonymous": 2,
#   "multiple_submit": false,
#   "autonumbering": false,
#   "page_after_submitformat": 1,
#   "publish_stats": false,
#   "completionsubmit": true,
#   "coursemodule": 239207,
#   "introfiles": [

#   ]
# }

# 3: get analyses
# @TODO we do not need _all_ feedbacks only employer info & student evaluation ones
# FIXME this doesn't work for some permissions reason, response JSON is:
# {'exception': 'required_capability_exception', 'errorcode': 'nopermission', 'message': 'error/nopermission'}
for fdbk in feedbacks:
    # or is it mod_feedback_get_responses_analysis?
    service = 'mod_feedback_get_analysis'
    params = {
        # see https://moodle.cca.edu/admin/settings.php?section=webservicetokens
        'wstoken': conf['TOKEN'],
        'wsfunction': service,
        'moodlewsrestformat': format,
        'feedbackid': fdbk['id']
    }
    response = get(conf['URL'], params=params)
    print(response.url)
    try:
        response.raise_for_status()
    except HTTPError:
        print(f'HTTP Error {response.status_code}')
        print(response.headers)
        print(response.text)

    data = response.json()
    print(data)
