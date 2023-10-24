import csv
import os

from dotenv import dotenv_values
from requests import get, HTTPError

# a tripartite set of API calls:
# 1. get all courses in the Internships category (may need to weed out demo/template courses)
# wsfunction: core_course_get_courses_by_field
# 2. get all Feedback activities from courses (1 request, no need for iteration)
# wsfunction: mod_feedback_get_feedbacks_by_courses
# 3. iterate over feedbacks, get all their analyses
# wsfunction: mod_feedback_get_analysis


conf = {
    **dotenv_values(".env"),  # load private env
    **os.environ,  # override loaded values with environment variables
}
conf["URL"] = conf["DOMAIN"] + "/webservice/rest/server.php"


def debug(s):
    """print message only if DEBUG env var is True

    Args:
        s (str): message to print
    """
    if conf.get("DEBUG") and bool(conf["DEBUG"]):
        print(s)


# 1 get courses
def get_courses():
    service = "core_course_get_courses_by_field"
    format = "json"
    params = {
        # see https://moodle.cca.edu/admin/settings.php?section=webservicetokens
        "wstoken": conf["TOKEN"],
        "wsfunction": service,
        "moodlewsrestformat": format,
        "field": "category",
        "value": conf["CATEGORY"],
    }

    response = get(conf["URL"], params=params)
    try:
        response.raise_for_status()
    except HTTPError:
        print(f"HTTP Error {response.status_code}")
        print(response.headers)
        print(response.text)

    data = response.json()
    debug(
        f'Found {len(data["courses"])} courses in category {conf["DOMAIN"]}/course/management.php?categoryid={conf["CATEGORY"]}'
    )
    # ? does it matter if we return full course objects or just IDs?
    return data["courses"]


def write_csv(feedback, id):
    filename = f"data/{id}-feedback.csv"
    # extract column names from first response, see get_feedbacks for structure
    column_labels = [
        response["name"] for response in feedback["anonattempts"][0]["responses"]
    ]

    with open(filename, mode="w") as file:
        writer = csv.writer(file)
        writer.writerow(column_labels)
        for attempt in feedback["anonattempts"]:
            row_values = [response["rawval"] for response in attempt["responses"]]
            writer.writerow(row_values)

    debug(f"Wrote {filename}")


def course_ids(courses):
    """return list of course ids from list of courses, skip ignored courses

    Args:
        courses (list[dict]): list of course dicts with at least an "id" property

    Returns:
        list[str]: list of course ids as strings
    """
    ids = [
        str(c["id"])
        for c in courses
        if str(c["id"]) not in conf["IGNORED_COURSES"].split(",")
    ]
    return ids


# 2: get feedbacks
def get_feedbacks(courses):
    ids = course_ids(courses)

    service = "mod_feedback_get_feedbacks_by_courses"
    format = "json"
    # ! this doesn't work, "Access control exception", but my token has all the necessary permissions
    # ! maybe because of the courseids param formatting?
    params = {
        # see https://moodle.cca.edu/admin/settings.php?section=webservicetokens
        "wstoken": conf["TOKEN"],
        "wsfunction": service,
        "moodlewsrestformat": format,
        "courseids[]": ",".join(ids),
    }
    # each course id is its own URL parameter, weird PHP behavior
    # ! there is probably a potential bug here where many courses -> too long URL
    # ! URLs can be 2048 chars and getting 2 courses is only 200 so maybe not
    for idx, id in enumerate(ids):
        params[f"courseids[{idx}]"] = id

    response = get(conf["URL"], params=params)
    try:
        response.raise_for_status()
    except HTTPError:
        print(f"HTTP Error {response.status_code}")
        print(response.headers)
        print(response.text)

    data = response.json()
    feedbacks = data.get("feedbacks", [])
    # example feedback structure:
    # {
    #   "id": 1520,
    #   "course": 5204,
    #   "name": "Submit Employer and Intern Information",
    #   "intro": "",
    #   "introformat": 1,
    #   "anonymous": 2,
    #   "multiple_submit": false,
    #   "autonumbering": f  alse,
    #   "page_after_submitformat": 1,
    #   "publish_stats": false,
    #   "completionsubmit": true,
    #   "coursemodule": 239207,
    #   "introfiles": []
    # }
    debug(f"Found {len(feedbacks)} Feedback activities")
    return feedbacks


# 3: get analyses
def get_responses(feedbacks):
    # TODO we do not need _all_ feedbacks only employer info & student evaluation ones
    for fdbk in feedbacks:
        # see note in readme about the difference between these 2 functions
        service = "mod_feedback_get_responses_analysis"
        # service = 'mod_feedback_get_analysis'
        format = "json"
        params = {
            "wstoken": conf["TOKEN"],
            "wsfunction": service,
            "moodlewsrestformat": format,
            "feedbackid": fdbk["id"],
        }
        response = get(conf["URL"], params=params)
        try:
            response.raise_for_status()
        except HTTPError:
            print(f"HTTP Error {response.status_code}")
            print(response.headers)
            print(response.text)

        data = response.json()
        # TODO handle warnings array & check for its presence in other wsfunction data
        # example analysis structure:
        # {
        #   "attempts": []
        #   "totalattempts": 0,
        #   "anonattempts": [
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
        #   "totalanonattempts": 10,
        #   "warnings": []
        # }
        # TODO return feedback, don't write csv
        debug(f'{len(data["anonattempts"])} attempts on Feedback {fdbk["id"]}')
        if data["totalanonattempts"] > 0:
            write_csv(data, fdbk["id"])


if __name__ == "__main__":
    courses = get_courses()
    feedbacks = get_feedbacks(courses)
    responses = get_responses(feedbacks)
    # ? how do we combine responses? hydrate each response with link to course/feedback it comes from?
