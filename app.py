import csv
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
# we may also need to get course information & somehow add it to the feedback results
# e.g. it might be important to know which program the internship was for


def write_csv(feedback, id):
    """ write a CSV of attempts given feedback attempts """
    if len(feedback["attempts"]) == 0:
        print(f"Feedback {id} has no attempts.")
        return

    filename = f"data/{id}-feedback.csv"
    # extract column names from first response
    column_labels = [response["name"] for response in feedback["attempts"][0]["responses"]]

    with open(filename, mode="w") as file:
        writer = csv.writer(file)
        writer.writerow(column_labels)
        for attempt in feedback["attempts"]:
            row_values = [response["rawval"] for response in attempt["responses"]]
            writer.writerow(row_values)

    print(f"Wrote {filename}")


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
try:
    response.raise_for_status()
except HTTPError:
    print(f'HTTP Error {response.status_code}')
    print(response.headers)
    print(response.text)

data = response.json()
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
#   "introfiles": []
# }

# 3: get analyses
# @TODO we do not need _all_ feedbacks only employer info & student evaluation ones
for fdbk in feedbacks:
    # see note in readme about the difference between these 2 functions
    service = 'mod_feedback_get_responses_analysis'
    # service = 'mod_feedback_get_analysis'
    params = {
        'wstoken': conf['TOKEN'],
        'wsfunction': service,
        'moodlewsrestformat': format,
        'feedbackid': fdbk['id']
    }
    response = get(conf['URL'], params=params)
    try:
        response.raise_for_status()
    except HTTPError:
        print(f'HTTP Error {response.status_code}')
        print(response.headers)
        print(response.text)

    data = response.json()
    # example analysis structure:
    # {
    #   "attempts": [
    #     {
    #       "id": 5817,
    #       "courseid": 0,
    #       "userid": 11,
    #       "timemodified": 1683236827,
    #       "fullname": "Rey .",
    #       "responses": [
    #         {
    #           "id": 10490,
    #           "name": "Your Phone Number",
    #           "printval": "323-123-9876",
    #           "rawval": "323-123-9876"
    #         },
    #   ...objects for each question, below is end of "attempts" array
    #   ],
    #   "totalattempts": 1,
    #   "anonattempts": [],
    #   "totalanonattempts": 0,
    #   "warnings": []
    # }
    write_csv(data, fdbk['id'])
