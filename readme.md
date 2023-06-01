# Combine Feedbacks

Combine the data contained in multiple Feedback activities into one unified CSV. For use with our Internships courses in Moodle which will have identically structured feedback activities with data we want to transfer to other systems for analysis and display.

## Moodle Web Services Setup

`poetry install` to get python dependencies.

See Moodle's [Web Services Overview](https://moodle.cca.edu/admin/settings.php?section=webservicesoverview) for their outline of setting up an API user.

- Create a new user of "Web Services" authentication
- Assign the user a Web Services User [System Role](https://moodle.cca.edu/admin/roles/assign.php?contextid=1)
- Create a [custom service](https://moodle.cca.edu/admin/settings.php?section=externalservices) for the app
  - **Enabled** for **Authorized users only** and (under "more") **Can download files**
  - **Required capabilities**: none [^1]
- Add all necessary web service functions to the service (basically, every REST API endpoint the script calls)
  - There's a list of functions in the [API Documentation](https://moodle.cca.edu/admin/webservice/documentation.php)
  - @TODO function for category get courses
  - `mod_feedback_get_feedbacks_by_courses`
  - `mod_feedback_get_analysis`
- Add the user created earlier as an authorized user of the new web service
- Ensure the user has the required capabilities in whatever context is needed
  - We put all Internships courses in one course category so we give the Web Services User role the `mod/feedback:viewanalysepage` and `mod/feedback:view` capabilities in that category
- [Create a token](https://moodle.cca.edu/admin/webservice/tokens.php?action=create) for the user, select the service, optionally set an expiration date if prudent. You may need to jump to the final page of tokens to see the one you just created.
- Copy example.env and paste the token value into it

[^1]: While some capabilities under mod_feedback _are_ required, we don't want to add them to the Web Services User role globally if we don't have to. Instead, we do not require them for the service, and we override the WSU role in the context of the course category we're using later.

## LICENSE

[ECL Version 2.0](https://opensource.org/licenses/ECL-2.0)
