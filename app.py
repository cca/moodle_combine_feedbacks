import csv
import os
import re

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


def http_error(resp):
    """print HTTP error details

    Args:
        resp (Response): HTTP response object from requests library
    """
    print(f"HTTP Error {resp.status_code}")
    print(resp.headers)
    print(resp.text)


# 1 get courses
def get_courses():
    """get all courses in the Internships category

    Returns:
        list[dict]: list of course dicts
    """
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
        http_error(response)

    data = response.json()
    debug(
        f'Found {len(data["courses"])} courses in category {conf["DOMAIN"]}/course/management.php?categoryid={conf["CATEGORY"]}'
    )
    return data["courses"]


def write_csv(feedbacks, label):
    """write feedbacks to a CSV file

    Args:
        feedbacks (list[dict]): list of feedback dicts with responses stored in anonattempts property
        label (str): label to use in the filename
    """
    filename = f"data/{label}-responses.csv"
    # example attempts structure:
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
    # extract columns from first response to first feedback
    columns = [
        # find (label) and extract it from parentheses
        re.match("^\(.*\)", r["name"].strip())[0][1:-1]
        for r in feedbacks[0]["anonattempts"][0]["responses"]
    ]

    # TODO use DictWriter instead? We want to be careful not to place the wrong values in a column
    with open(filename, mode="w") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        for feedback in feedbacks:
            for attempt in feedback["anonattempts"]:
                # use the "printval" property for Connection question, rawval for others
                row = []
                for response in attempt["responses"]:
                    if re.match("\(connection\)", response["name"].lower()):
                        row.append(response["printval"])
                    else:
                        row.append(response["rawval"])
                writer.writerow(row)

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
    """given a list of courses, return the feedback activities within them

    Args:
        courses (list[dict]): list of course dicts containing at least an id property

    Returns:
        list[dict]: list of feedback activity dicts
    """
    ids = course_ids(courses)

    service = "mod_feedback_get_feedbacks_by_courses"
    format = "json"
    params = {
        # see https://moodle.cca.edu/admin/settings.php?section=webservicetokens
        "wstoken": conf["TOKEN"],
        "wsfunction": service,
        "moodlewsrestformat": format,
        "courseids[]": ",".join(ids),
    }
    # each course id is its own URL parameter, weird PHP behavior
    # ! there is probably a potential bug here where many courses -> too long URL
    # ! URLs can be 2048 chars and getting 2 courses is only ≈200 so maybe not
    # ! also unclear if Moodle has a limit on the number of feedbacks it returns
    for idx, id in enumerate(ids):
        params[f"courseids[{idx}]"] = id

    response = get(conf["URL"], params=params)
    try:
        response.raise_for_status()
    except HTTPError:
        http_error(response)

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


def feedback_type(feedback):
    """classify feedback as either an internship information or evaluation activity, or neither
    the returned string must match the name of the list in get_responses that it's appended to

    Args:
        feedback (dict): feedback dict with name property

    Returns:
        str|None: either "internships", "evaluations", or None
    """
    # trim whitespace and lowercase for easier matching
    name = feedback["name"].lower().strip()
    if "submit employer and intern information" in name:
        return "internships"
    elif "evaluation" in name:
        return "evaluations"
    else:
        return None


# 3: get analyses
def get_responses(feedbacks):
    """given a list of feedback activities, return two lists of responses:
    1. internship information ("Employer and Intern Information" feedbacks)
    2. student evaluations ("Evaluation" feedbacks)

    Args:
        feedbacks (list[dict]): list of feeedback activity dicts

    Returns:
        list[dict], list[dict]: list of internship responses, list of evaluation responses
    """
    internships = []
    evaluations = []
    for fdbk in feedbacks:
        # skip feedbacks that aren't internships or evaluations
        type = feedback_type(fdbk)
        if type:
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
                http_error(response)

            data = response.json()
            # TODO handle warnings array & check for its presence in other wsfunction data
            # example analysis structure:
            # {
            #   "attempts": []
            #   "totalattempts": 0,
            #   "anonattempts": [...],
            #   "totalanonattempts": 10,
            #   "warnings": []
            # }
            debug(
                f'{len(data["anonattempts"])} attempts on Feedback {fdbk["id"]} {conf["DOMAIN"] + "/mod/feedback/show_entries.php?id=" + str(fdbk["coursemodule"])}'
            )

            if data["totalanonattempts"] > 0:
                locals()[type].append(data)

    return internships, evaluations


if __name__ == "__main__":
    courses = get_courses()
    feedbacks = get_feedbacks(courses)
    internships, evaluations = get_responses(feedbacks)
    write_csv(internships, "internships")
    write_csv(evaluations, "evaluations")
