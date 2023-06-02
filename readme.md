# Combine Feedbacks

Combine the data contained in multiple Feedback activities into one unified CSV. For use with our Internships courses in Moodle which will have identically structured feedback activities with data we want to transfer to other systems for analysis and display.

## Moodle Web Services Setup

`poetry install` to get python dependencies.

See Moodle's [Web Services Overview](https://moodle.cca.edu/admin/settings.php?section=webservicesoverview) for their outline of setting up an API user. Normally, we would create a user of the "Web Services" authentication type, put it in the Web Services User role, and give that role the needed capabilities in the right context. However, after doing that, calls to the `mod_feedback_get_analysis` function still failed with a `required_capability_exception`. So below we use an account that is one of the site administrators.

- Create a [custom service](https://moodle.cca.edu/admin/settings.php?section=externalservices) for the app
  - **Enabled** for **Authorized users only** and (under "more") **Can download files**
  - **Required capabilities**: `mod/feedback:viewanalysepage`, `mod/feedback:view`, `mod/feedback:viewreports`, @TODO more
- Add all necessary web service functions to the service (basically, every REST API endpoint the script calls)
  - There's a list of functions in the [API Documentation](https://moodle.cca.edu/admin/webservice/documentation.php)
  - @TODO function for category get courses
  - `mod_feedback_get_feedbacks_by_courses`
  - `mod_feedback_get_analysis`
  - `mod_feedback_get_responses_analysis`
- Add a site admin user as an authorized user of the service
- [Create a token](https://moodle.cca.edu/admin/webservice/tokens.php?action=create) for the user, select the service, optionally set an expiration date if prudent. You may need to jump to the final page of tokens to see the one you just created.
- Copy example.env to .env and paste the token value into it

## Two WS Functions

@TODO Only one of `mod_feedback_get_analysis` or `mod_feedback_get_responses_analysis` is needed. The former gives a lot more information about how the questions are structured and then puts all responses in a `data` array under the question, while the latter is more focused on the response data, collecting all attempts into an array where each response contains the name of the field and two different values ("print" versus "raw"). It's highly likely we will want to use the second API and remove the first from the service. One notable difference: `get_analysis` doesn't actually link back to the user who submitted, while `get_responses_analysis` does (it gives us their ID and full name). We could chain the user id into a user profile API call to fill in more information about them.

## LICENSE

[ECL Version 2.0](https://opensource.org/licenses/ECL-2.0)
