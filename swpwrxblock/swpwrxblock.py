"""
StepWise Power xblock questions can contain up to 10 variants.  The xblock remembers which variants the student has attempted and if the student
requests a new variant, we will try to assign one that has not yet been attempted. Once the student has attempted all available variants,
if they request another variant, we will clear the list of attempted variants and start assigning variants over again.

We count question attempts made by the student.  We don't consider an attempt to have begun until the student submits their first step
in the attempt, or requests a hint, or requests to see the worked-out solution ('ShowMe').
We use a callback from the StepWise UI client code to know that the student has begun their attempt.

An attempt isn't counted until the student submits their first step since the student can visit the question, then leave the question
without doing any work, and come back later.  We don't want to wait until after the student submits their final answer to count the attempt
to prevent the student from (1) visiting the problem, (2) clicking show solution, (3) writing down the steps, and (4) reloading the browser
web page.  In this scenario the student has seen the steps to the solution, but is not charged for an attempt.

When the student completes work on the StepWise problem ('victory'), we use a callback from the StepWise UI client code to record
the student's score on that attempt.

The Javascript code in this xblock displays the score and steps on the student's most recent attempt (only).

Note that the xblock Python code's logic for computing the score is somewhat duplicated in the xblock's Javascript code since the Javascript is
responsible for updating the information displayed to the student on their results, and the Python code does not currently provide
this detailed scoring data down to the Javascript code.  It may be possible for the results of the scoring callback POST to return
the scoring details to the Javascript code for display, but this is not currently done.  Thus, if you need to update the scoring logic
here in Python, you need to check the Javascript source in js/src/swpwrxstudent.js to make sure you don't also have to change the score display
logic there.

The swpwr_problem_hints field is optional, and looks like this:
swpwr.problem.wpHints = [
  {
    "pageId": "newbWorkProblem",
    "hints":[
        "helpful hint",
        "Even more helpful",
        "Fricken enlightenment"
    ]
  },
  { // another page
  },
  {
    // yet another page
  },
]

The flow of saving results is:
   swpwrxstudent.js sets the callback URLs for saving partial results (per step), and saving final results (on problem complete).
   For save_swpwr_final_results(data), we do:
        (A) set self.swpwr_results = json.dumps(data)
        (B) set self.is_answered=True
        (C) call save_grade(data), which should
            (1) set self.solution=data
            (2) set self.grade=grade
            (3) call self.save() , which does:
                (a) sets the url_name field with a UUID so we have a unique identifier
                (b) calls XBlock.save() to persist our object data
        (D) publish_grade,  which should call
              self.runtime.publish

    save_swpwr_partial_results(data) does the same as save_swpwr_final_results(),
        except it sets self.is_answered=False

NOTE: the url_name field in this xblock records a UUID for this xblock instance. This url_name field was added so this xblock looks like every other
      standard type of xblock to the OpenEdX runtime (e.g chapter, sequential, vertical, problem).
      Having the url_name field in the xblock makes it easier to generate unique xblocks via software, e.g. from StepWise questions defined in Jira.
      If a url_name field exists in the xblock, then OpenEdX apparently uses that field value to uniquely identify the object.
      Without filling in a value in this field, course imports of XML swpwrxblock data will mess up and all xblocks with a blank value for url_name
      will be assumed to be the same xblock, which causes the import to mangle the swpwrxblocks in the course import.
      To ensure that we have a unique value for url_field, the save() routine checks the url_name field and if it is blank, we generate a UUID to 
      provide a value for that field.  Doing the creation of this field in this manner means that we don't have to expose the url_name field in
      The studio view and make a question author invent a unique url_name value for their question.

"""

# Python stuff
import pkg_resources
import random
import json
import re
import uuid

from logging import getLogger


# Django Stuff
from django.conf import settings

# Open edX stuff
from xblock.core import XBlock
from xblock.fields import Integer, String, Scope, Dict, Float, Boolean
from web_fragments.fragment import Fragment
# McDaniel apr-2019: this is deprecated.
#from xblock.fragment import Fragment
from xblock.scorable import ScorableXBlockMixin, Score
from xblockutils.studio_editable import StudioEditableXBlockMixin
from lms.djangoapps.courseware.courses import get_course_by_id
# Fuka sep-2024 this is deprecated
# from xblock.mixins import ScopedStorageMixin


UNSET = object()

logger = getLogger(__name__)

#DEBUG=settings.ROVER_DEBUG
# DEBUG=False
DEBUG=True

DEFAULT_RANK="cadet"  # What we'll use for a rank if not modified by the user/default
TEST_MODE=False

"""
The general idea is that we'll determine which question parameters to pass to the StepWise client before invoking it,
making use of course-wide StepWise defaults if set.
If the student has exceeded the max mumber of attempts (course-wide setting or per-question setting), we won't let them
start another attempt.
We'll then get two call-backs:
1. When the student begins work on the question (e.g. submits a first step, clicks 'Hint', or clicks 'Show Solution',
the callback code here will increment the attempts counter.
2. When the student completes the problem ('victory'), we'll compute their grade and save their grade for this attempt.
Note that the student can start an attempt, but never finish (abandoned attempt), but we will still want to count that attempt.
"""

@XBlock.wants('user')
class SWPWRXBlock(StudioEditableXBlockMixin, ScorableXBlockMixin, XBlock):
    """
    This xblock provides up to 10 variants of a question for delivery using the StepWise UI.
    """

    has_author_view = True # tells the xblock to not ignore the AuthorView
    has_score = True       # tells the xblock to not ignore the grade event
    show_in_read_only_mode = True # tells the xblock to let the instructor view the student's work (lms/djangoapps/courseware/masquerade.py)

    MAX_VARIANTS = 1	   # This code handles 1 variant

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    # Place to store the UUID for this xblock instance.  Not currently displayed in any view.
    url_name = String(display_name="URL name", default='NONE', scope=Scope.content)

    # PER-QUESTION GRADING OPTIONS (SEPARATE SET FOR COURSE DEFAULTS)
    q_weight = Float(
        display_name="Problem Weight",
        help="Defines the number of points the problem is worth.",
        scope=Scope.content,
        default=1.0,
        enforce_type=True
    )

# NOTE: Don't assume 3 points per problem in swpwrxblock
    # q_grade_showme_ded = Float(display_name="Point deduction for using Show Solution",help="SWPWR Raw points deducted from 3.0 (Default: 3.0)", default=3.0, scope=Scope.content)
    q_grade_showme_ded = Float(display_name="Point deduction for using Show Solution",help="SWPWR Raw points deducted from 1.0 (Default: 0.25)", default=0.25, scope=Scope.content)
    q_grade_hints_count = Integer(help="SWPWR Number of Hints before deduction", default=2, scope=Scope.content)
    q_grade_hints_ded = Float(help="SWPWR Point deduction for using excessive Hints", default=1.0, scope=Scope.content)
    q_grade_errors_count = Integer(help="SWPWR Number of Errors before deduction", default=2, scope=Scope.content)
    q_grade_errors_ded = Float(help="SWPWR Point deduction for excessive Errors", default=1.0, scope=Scope.content)
    q_grade_min_steps_count = Integer(help="SWPWR Minimum valid steps in solution for full credit", default=3, scope=Scope.content)
    q_grade_min_steps_ded = Float(help="SWPWR Point deduction for fewer than minimum valid steps", default=0.25, scope=Scope.content)
# NOTE: Don't assume 3 points per problem in swpwrxblock, so don't deduct 0.25 in swpwrxblock for min steps
    # q_grade_min_steps_ded = Float(help="SWPWR Point deduction for fewer than minimum valid steps", default=0.25, scope=Scope.content)
    q_grade_app_key = String(help="SWPWR question app key", default="SBIRPhase2", scope=Scope.content);

    # PER-QUESTION HINTS/SHOW SOLUTION OPTIONS
    q_option_hint = Boolean(help='SWPWR Display Hint button if "True"', default=True, scope=Scope.content)
    q_option_showme = Boolean(help='SWPWR Display ShowSolution button if "True"', default=True, scope=Scope.content)

    # MAX ATTEMPTS PER-QUESTION OVERRIDE OF COURSE DEFAULT
    q_max_attempts = Integer(help="SWPWR Max question attempts (-1 = Use Course Default)", default=-1, scope=Scope.content)

    # STEP-WISE QUESTION DEFINITION FIELDS FOR VARIANTS
    display_name = String(display_name="SWPWR Display name", default='SWPWR', scope=Scope.content)

    q_id = String(help="Question ID", default="", scope=Scope.content)
    q_label = String(help="SWPWR Question label", default="", scope=Scope.content)
    q_stimulus = String(help="SWPWR Stimulus", default='Solve for \\(a\\). \\(5a+4=2a-5\\)', scope=Scope.content)
    q_definition = String(help="SWPWR Definition", default='SolveFor[5a+4=2a-5,a]', scope=Scope.content)
    q_type = String(help="SWPWR Type", default='gradeBasicAlgebra', scope=Scope.content)
    q_display_math = String(help="SWPWR Display Math", default='\\(\\)', scope=Scope.content)
    q_hint1 = String(help="SWPWR First Math Hint", default='', scope=Scope.content)
    q_hint2 = String(help="SWPWR Second Math Hint", default='', scope=Scope.content)
    q_hint3 = String(help="SWPWR Third Math Hint", default='', scope=Scope.content)
    q_swpwr_problem = String(help="SWPWR SWPWR Problem", default='', scope=Scope.content)
    # Invalid schema choices should be a CSV list of one or more of these: "TOTAL", "DIFFERENCE", "CHANGEINCREASE", "CHANGEDECREASE", "EQUALGROUPS", and "COMPARE"
    # Invalid schema choices can also be the official names: "additiveTotalSchema", "additiveDifferenceSchema", "additiveChangeSchema", "subtractiveChangeSchema", "multiplicativeEqualGroupsSchema", and "multiplicativeCompareSchema"
    # This Xblock converts the upper-case names to the official names when constructing the launch code for the React app, so you can mix these names.
    # Note that this code doesn't validate these schema names, so Caveat Utilitor.
    q_swpwr_invalid_schemas = String(display_name="Comma-separated list of unallowed schema names", help="SWPWR Comma-seprated list of unallowed schema names", default="",scope=Scope.content)
    # Rank choices should be "newb" or "cadet" or "learner" or "ranger"
    q_swpwr_rank = String(display_name="Student rank for this question", help="SWPWR Student rank for this question", default=DEFAULT_RANK, scope=Scope.content)
    q_swpwr_problem_hints = String(display_name="Problem-specific hints (JSON)", help="SWPWR optional problem-specific hints (JSON)", default="[]", scope=Scope.content)
    # STUDENT'S QUESTION PERFORMANCE FIELDS
    swpwr_results = String(help="SWPWR The student's SWPWR Solution structure", default="", scope=Scope.user_state)

    xb_user_username = String(help="SWPWR The user's username", default="", scope=Scope.user_state)
    xb_user_fullname = String(help="SWPWR The user's fullname", default="", scope=Scope.user_state)
    grade = Float(help="SWPWR The student's grade", default=-1, scope=Scope.user_state)
    solution = Dict(help="SWPWR The student's last stepwise solution", default={}, scope=Scope.user_state)
    question = Dict(help="SWPWR The student's current stepwise question", default={}, scope=Scope.user_state)
    # count_attempts keeps track of the number of attempts of this question by this student so we can
    # compare to course.max_attempts which is inherited as an per-question setting or a course-wide setting.
    count_attempts = Integer(help="SWPWR Counted number of questions attempts", default=0, scope=Scope.user_state)
    raw_possible = Float(help="SWPWR Number of possible points", default=1,scope=Scope.user_state)
# NOTE: Don't assume 3 points per problem in swpwrxblock
    # raw_possible = Float(help="SWPWR Number of possible points", default=3,scope=Scope.user_state)
    # The following 'weight' is examined by the standard scoring code, so needs to be set once we determine which weight value to use
    # (per-Q or per-course). Also used in rescoring by override_score_module_state.
    weight = Float(help="SWPWR Defines the number of points the problem is worth.", default=1, scope=Scope.user_state)

    my_weight  = Integer(help="SWPWR Remember weight course setting vs question setting", default=-1, scope=Scope.user_state)
    my_max_attempts  = Integer(help="SWPWR Remember max_attempts course setting vs question setting", default=-1, scope=Scope.user_state)
    my_option_showme  = Integer(help="SWPWR Remember option_showme course setting vs question setting", default=-1, scope=Scope.user_state)
    my_option_hint  = Integer(help="SWPWR Remember option_hint course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_showme_ded  = Integer(help="SWPWR Remember grade_showme_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_hints_count  = Integer(help="SWPWR Remember grade_hints_count course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_hints_ded  = Integer(help="SWPWR Remember grade_hints_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_errors_count  = Integer(help="SWPWR Remember grade_errors_count course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_errors_ded  = Integer(help="SWPWR Remember grade_errors_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_min_steps_count  = Integer(help="SWPWR Remember grade_min_steps_count course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_min_steps_ded  = Integer(help="SWPWR Remember grade_min_steps_ded course setting vs question setting", default=-1, scope=Scope.user_state)
    my_grade_app_key  = String(help="SWPWR Remember app_key course setting vs question setting", default="SBIRPhase2", scope=Scope.user_state)

    # variant_attempted: Remembers the set of variant q_index values the student has already attempted.
    # We can't add a Set to Scope.user_state, or we get get runtime errors whenever we update this field:
    #      variants_attempted = Set(scope=Scope.user_state)
    #      TypeError: Object of type set is not JSON serializable
    # See e.g. this:  https://stackoverflow.com/questions/8230315/how-to-json-serialize-sets
    # So we'll leave the variants in an Integer field and fiddle the bits ourselves :-(
    # We define our own bitwise utility functions below: bit_count_ones() bit_is_set() bit_is_set()

    variants_attempted = Integer(help="SWPWR Bitmap of attempted variants", default=0,scope=Scope.user_state)
    variants_count = Integer(help="SWPWR Count of available variants", default=0,scope=Scope.user_state)
    previous_variant = Integer(help="SWPWR Index (q_index) of the last variant used", default=-1,scope=Scope.user_state)

    # FIELDS FOR THE ScorableXBlockMixin

    is_answered = Boolean(
        default=False,
        scope=Scope.user_state,
        help='Will be set to "True" if successfully answered'
    )

    correct = Boolean(
        default=False,
        scope=Scope.user_state,
        help='Will be set to "True" if correctly answered'
    )

    raw_earned = Float(
        help="SWPWR Keeps maximum score achieved by student as a raw value between 0 and 1.",
        scope=Scope.user_state,
        default=0,
        enforce_type=True,
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # STUDENT_VIEW
    def student_view(self, context=None):
        """
        The STUDENT view of the SWPWRXBlock, shown to students
        when viewing courses.  We set up the question parameters (referring to course-wide settings), then launch
        the javascript StepWise client.
        """
        if DEBUG: logger.info('SWPWRXBlock student_view() entered. context={context}'.format(context=context))

        if DEBUG: logger.info("SWPWRXBlock student_view() self={a}".format(a=self))
        if DEBUG: logger.info("SWPWRXBlock student_view() self.runtime={a}".format(a=self.runtime))
        if DEBUG: logger.info("SWPWRXBlock student_view() self.runtime.course_id={a}".format(a=self.runtime.course_id))
        if DEBUG: logger.info("SWPWRXBlock student_view() self.variants_attempted={v}".format(v=self.variants_attempted))
        if DEBUG: logger.info("SWPWRXBlock student_view() self.previous_variant={v}".format(v=self.previous_variant))

        course = get_course_by_id(self.runtime.course_id)
        if DEBUG: logger.info("SWPWRXBlock student_view() course={c}".format(c=course))

        if DEBUG: logger.info("SWPWRXBlock student_view() max_attempts={a} q_max_attempts={b}".format(a=self.max_attempts,b=self.q_max_attempts))

        # NOTE: Can't set a self.q_* field here if an older imported swpwrxblock doesn't define this field, since it defaults to None
        # (read only?) so we'll use instance vars my_* to remember whether to use the course-wide setting or the per-question setting.
        # Similarly, some old courses may not define the stepwise advanced settings we want, so we create local variables for them.

        # For per-xblock settings
        temp_weight = -1
        temp_max_attempts = -1
        temp_option_hint = -1
        temp_option_showme = -1
        temp_grade_shome_ded = -1
        temp_grade_hints_count = -1
        temp_grade_hints_ded = -1
        temp_grade_errors_count = -1
        temp_grade_errors_ded = -1
        temp_grade_min_steps_count = -1
        temp_grade_min_steps_ded = -1
        temp_grade_app_key = ""

        # For course-wide settings
        temp_course_stepwise_weight = -1
        temp_course_stepwise_max_attempts = -1
        temp_course_stepwise_option_hint = -1
        temp_course_stepwise_option_showme = -1
        temp_course_stepwise_grade_showme_ded = -1
        temp_course_stepwise_grade_hints_count = -1
        temp_course_stepwise_grade_hints_ded = -1
        temp_course_stepwise_grade_errors_count = -1
        temp_course_stepwise_grade_errors_ded = -1
        temp_course_stepwise_grade_min_steps_count = -1
        temp_course_stepwise_grade_min_steps_ded = -1
        temp_course_stepwise_grade_app_key = ""

        # Defaults For course-wide settings if they aren't defined for this course
        def_course_stepwise_weight = 1.0
        def_course_stepwise_max_attempts = None
        def_course_stepwise_option_hint = True
        def_course_stepwise_option_showme = True
        def_course_stepwise_grade_showme_ded = 0.25
# NOTE: Don't assume 3 points per problem in swpwrxblock
        # def_course_stepwise_grade_showme_ded = 3.0
        def_course_stepwise_grade_hints_count = 2
        def_course_stepwise_grade_hints_ded = 1.0
        def_course_stepwise_grade_errors_count = 2
        def_course_stepwise_grade_errors_ded = 1.0
        def_course_stepwise_grade_min_steps_count = 3
        def_course_stepwise_grade_min_steps_ded = 0.0
# NOTE: Don't assume a min steps deduction in swpwrxblock
        # def_course_stepwise_grade_min_steps_ded = 0.25
        def_course_stepwise_grade_app_key = "SBIRPhase2"

        # after application of course-wide settings
        self.my_weight = -1
        self.my_max_attempts = -1
        self.my_option_showme = -1
        self.my_option_hint = -1
        self.my_grade_showme_ded = -1
        self.my_grade_hints_count = -1
        self.my_grade_hints_ded = -1
        self.my_grade_errors_count = -1
        self.my_grade_errors_ded = -1
        self.my_grade_min_steps_count = -1
        self.my_grade_min_steps_ded = -1
        self.my_grade_app_key = ""

        # Fetch the xblock-specific settings if they exist, otherwise create a default
      

        try:
            temp_weight = self.q_weight
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_weight was not defined in this instance: {e}'.format(e=e))
            temp_weight = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_weight: {t}'.format(t=temp_weight))

        try:
            temp_max_attempts = self.q_max_attempts
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_max_attempts was not defined in this instance: {e}'.format(e=e))
            temp_max_attempts = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_max_attempts: {t}'.format(t=temp_max_attempts))

        try:
            temp_option_hint = self.q_option_hint
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.option_hint was not defined in this instance: {e}'.format(e=e))
            temp_option_hint = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_option_hint: {t}'.format(t=temp_option_hint))

        try:
            temp_option_showme = self.q_option_showme
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.option_showme was not defined in this instance: {e}'.format(e=e))
            temp_option_showme = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_option_showme: {t}'.format(t=temp_option_showme))

        try:
            temp_grade_showme_ded = self.q_grade_showme_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_showme_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_showme_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_showme_ded: {t}'.format(t=temp_grade_showme_ded))

        try:
            temp_grade_hints_count = self.q_grade_hints_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_hints_count was not defined in this instance: {e}'.format(e=e))
            temp_grade_hints_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_hints_count: {t}'.format(t=temp_grade_hints_count))

        try:
            temp_grade_hints_ded = self.q_grade_hints_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_hints_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_hints_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_hints_ded: {t}'.format(t=temp_grade_hints_ded))

        try:
            temp_grade_errors_count = self.q_grade_errors_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_errors_count was not defined in this instance: {e}'.format(e=e))
            temp_grade_errors_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_errors_count: {t}'.format(t=temp_grade_errors_count))

        try:
            temp_grade_errors_ded = self.q_grade_errors_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_errors_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_errors_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_errors_ded: {t}'.format(t=temp_grade_errors_ded))

        try:
            temp_grade_min_steps_count = self.q_grade_min_steps_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_min_steps_count was not defined in this instance: {e}'.format(e=e))
            temp_grade_min_steps_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_min_steps_count: {t}'.format(t=temp_grade_min_steps_count))

        try:
            temp_grade_min_steps_ded = self.q_grade_min_steps_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_min_steps_ded was not defined in this instance: {e}'.format(e=e))
            temp_grade_min_steps_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_min_steps_ded: {t}'.format(t=temp_grade_min_steps_ded))

        try:
            temp_grade_app_key = self.q_grade_app_key
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_grade_app_key was not defined in this instance: {e}'.format(e=e))
            temp_grade_app_key = ""
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_grade_app_key: {t}'.format(t=temp_grade_app_key))

        # Fetch the course-wide settings if they exist, otherwise create a default

        try:
            temp_course_stepwise_weight = course.stepwise_weight
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_weight was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_stepwise_weight = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_weight: {s}'.format(s=temp_course_stepwise_weight))

        try:
            temp_course_stepwise_max_attempts = course.stepwise_max_attempts
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_max_attempts was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_stepwise_max_attempts = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_max_attempts: {s}'.format(s=temp_course_stepwise_max_attempts))

        try:
            temp_course_stepwise_option_showme = course.stepwise_option_showme
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_option_showme was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_option_showme = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_option_showme: {s}'.format(s=temp_course_stepwise_option_showme))

        try:
            temp_course_stepwise_option_hint = course.stepwise_option_hint
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_option_hint was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_option_hint = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_option_hint: {s}'.format(s=temp_course_stepwise_option_hint))

        try:
            temp_course_stepwise_grade_hints_count = course.stepwise_grade_hints_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_settings_grade_hints_count was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_hints_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_hints_count: {s}'.format(s=temp_course_stepwise_grade_hints_count))

        try:
            temp_course_stepwise_grade_showme_ded = course.stepwise_grade_showme_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_showme_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_showme_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_showme_ded: {s}'.format(s=temp_course_stepwise_grade_showme_ded))

        try:
            temp_course_stepwise_grade_hints_ded = course.stepwise_grade_hints_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_hints_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_hints_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_hints_ded: {s}'.format(s=temp_course_stepwise_grade_hints_ded))

        try:
            temp_course_stepwise_grade_errors_count = course.stepwise_grade_errors_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_errors_count was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_errors_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_errors_count: {s}'.format(s=temp_course_stepwise_grade_errors_count))

        try:
            temp_course_stepwise_grade_errors_ded = course.stepwise_grade_errors_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_errors_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_errors_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_errors_ded: {s}'.format(s=temp_course_stepwise_grade_errors_ded))

        try:
            temp_course_stepwise_grade_min_steps_count = course.stepwise_grade_min_steps_count
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_min_steps_count was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_min_steps_count = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_min_steps_count: {s}'.format(s=temp_course_stepwise_grade_min_steps_count))

        try:
            temp_course_stepwise_grade_min_steps_ded = course.stepwise_grade_min_steps_ded
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_min_steps_ded was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_min_steps_ded = -1
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_min_steps_ded: {s}'.format(s=temp_course_stepwise_grade_min_steps_ded))

        try:
            temp_course_stepwise_app_key = course.stepwise_grade_app_key
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() course.stepwise_grade_app_key was not defined in this instance: {e}'.format(e=e))
            temp_course_stepwise_grade_app_key = ""
        if DEBUG: logger.info('SWPWRXBlock student_view() temp_course_stepwise_grade_app_key: {s}'.format(s=temp_course_stepwise_grade_app_key))

        # Enforce course-wide grading options here.
        # We prefer the per-question setting to the course setting.
        # If neither the question setting nor the course setting exist, use the course default.

        if (temp_weight != -1):
            self.my_weight = temp_weight
        elif (temp_course_stepwise_weight != -1):
            self.my_weight = temp_course_stepwise_weight
        else:
            self.my_weight = def_course_stepwise_weight
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_weight={m}'.format(m=self.my_weight))

        # Set the real object weight here how that we know all of the weight settings (per-Q vs. per-course).
        # weight is used by the real grading code e.g. for overriding student scores.
        self.weight = self.my_weight
        if DEBUG: logger.info('SWPWRXBlock student_view() self.weight={m}'.format(m=self.weight))

        # For max_attempts: If there is a per-question max_attempts setting, use that.
        # Otherwise, if there is a course-wide stepwise_max_attempts setting, use that.
        # Otherwise, use the course-wide max_attempts setting that is used for CAPA (non-StepWise) problems.

        if temp_max_attempts is None:
            temp_max_attempts = -1

        if (temp_max_attempts != -1):
            self.my_max_attempts = temp_max_attempts
            if DEBUG: logger.info('SWPWRXBlock student_view() my_max_attempts={a} temp_max_attempts={m}'.format(a=self.my_max_attempts,m=temp_max_attempts))
        elif (temp_course_stepwise_max_attempts != -1):
            self.my_max_attempts = temp_course_stepwise_max_attempts
            if DEBUG: logger.info('SWPWRXBlock student_view() my_max_attempts={a} temp_course_stepwise_max_attempts={m}'.format(a=self.my_max_attempts,m=temp_course_stepwise_max_attempts))
        else:
            self.my_max_attempts = course.max_attempts
            if DEBUG: logger.info('SWPWRXBlock student_view() my_max_attempts={a} course.max_attempts={m}'.format(a=self.my_max_attempts,m=course.max_attempts))

        if (temp_option_hint != -1):
            self.my_option_hint = temp_option_hint
        elif (temp_course_stepwise_option_hint != -1):
            self.my_option_hint = temp_course_stepwise_option_hint
        else:
            self.my_option_hint = def_course_stepwise_option_hint
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_option_hint={m}'.format(m=self.my_option_hint))

        if (temp_option_showme != -1):
            self.my_option_showme = temp_option_showme
        elif (temp_course_stepwise_option_showme != -1):
            self.my_option_showme = temp_course_stepwise_option_showme
        else:
            self.my_option_showme = def_course_stepwise_option_showme
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_option_showme={m}'.format(m=self.my_option_showme))

        if (temp_grade_showme_ded != -1):
            self.my_grade_showme_ded = temp_grade_showme_ded
        elif (temp_course_stepwise_grade_showme_ded != -1):
            self.my_grade_showme_ded = temp_course_stepwise_grade_showme_ded
        else:
            self.my_grade_showme_ded = def_course_stepwise_grade_showme_ded
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_showme_ded={m}'.format(m=self.my_grade_showme_ded))

        if (temp_grade_hints_count != -1):
            self.my_grade_hints_count = temp_grade_hints_count
        elif (temp_course_stepwise_grade_hints_count != -1):
            self.my_grade_hints_count = temp_course_stepwise_grade_hints_count
        else:
            self.my_grade_hints_count = def_course_stepwise_grade_hints_count
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_hints_count={m}'.format(m=self.my_grade_hints_count))

        if (temp_grade_hints_ded != -1):
            self.my_grade_hints_ded = temp_grade_hints_ded
        elif (temp_course_stepwise_grade_hints_ded != -1):
            self.my_grade_hints_ded = temp_course_stepwise_grade_hints_ded
        else:
            self.my_grade_hints_ded = def_course_stepwise_grade_hints_ded
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_hints_ded={m}'.format(m=self.my_grade_hints_ded))

        if (temp_grade_errors_count != -1):
            self.my_grade_errors_count = temp_grade_errors_count
        elif (temp_course_stepwise_grade_errors_count != -1):
            self.my_grade_errors_count = temp_course_stepwise_grade_errors_count
        else:
            self.my_grade_errors_count = def_course_stepwise_grade_errors_count
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_errors_count={m}'.format(m=self.my_grade_errors_count))

        if (temp_grade_errors_ded != -1):
            self.my_grade_errors_ded = temp_grade_errors_ded
        elif (temp_course_stepwise_grade_errors_ded != -1):
            self.my_grade_errors_ded = temp_course_stepwise_grade_errors_ded
        else:
            self.my_grade_errors_ded = def_course_stepwise_grade_errors_ded
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_errors_ded={m}'.format(m=self.my_grade_errors_ded))

        if (temp_grade_min_steps_count != -1):
            self.my_grade_min_steps_count = temp_grade_min_steps_count
        elif (temp_course_stepwise_grade_min_steps_count != -1):
            self.my_grade_min_steps_count = temp_course_stepwise_grade_min_steps_count
        else:
            self.my_grade_min_steps_count = def_course_stepwise_grade_min_steps_count
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_min_steps_count={m}'.format(m=self.my_grade_min_steps_count))

        if (temp_grade_min_steps_ded != -1):
            self.my_grade_min_steps_ded = temp_grade_min_steps_ded
        elif (temp_course_stepwise_grade_min_steps_ded != -1):
            self.my_grade_min_steps_ded = temp_course_stepwise_grade_min_steps_ded
        else:
            self.my_grade_min_steps_ded = def_course_stepwise_grade_min_steps_ded
        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_min_steps_ded={m}'.format(m=self.my_grade_min_steps_ded))

        if (temp_grade_app_key != ""):
            self.my_grade_app_key = temp_grade_app_key
        elif (temp_course_stepwise_grade_app_key != ""):
            self.my_grade_app_key = temp_course_stepwise_grade_app_key
        else:
            self.my_grade_app_key = def_course_stepwise_grade_app_key

        if DEBUG: logger.info('SWPWRXBlock student_view() self.my_grade_app_key={m}'.format(m=self.my_grade_app_key))

        # Fetch the new xblock-specific attributes if they exist, otherwise set them to a default
        try:
            temp_value = self.q_swpwr_invalid_schemas
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_invalid_schemas was not defined in this instance: {e}'.format(e=e))
            self.q_swpwr_invalid_schemas = ""
        if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_invalid_schemas: {t}'.format(t=self.q_swpwr_invalid_schemas))
        try:
            temp_value = self.q_swpwr_rank
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_rank was not defined in this instance: {e}'.format(e=e))
            self.q_swpwr_rank = DEFAULT_RANK
        if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_rank: {t}'.format(t=self.q_swpwr_rank))
        try:
            temp_value = self.q_swpwr_problem_hints
        except (NameError,AttributeError) as e:
            if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_problem_hints was not defined in this instance: {e}'.format(e=e))
            self.q_swpwr_problem_hints = "[]"
        if DEBUG: logger.info('SWPWRXBlock student_view() self.q_swpwr_problem_hints: {t}'.format(t=self.q_swpwr_problem_hints))

        # Save an identifier for the user and their full name

        user_service = self.runtime.service( self, 'user')
        xb_user = user_service.get_current_user()
        self.xb_user_username = user_service.get_current_user().opt_attrs.get('edx-platform.username')
        if self.xb_user_username is None:
            if DEBUG: logger.error('SWPWRXBlock self.xb_user_username was None')
            self.xb_user_username = 'FIXME'
        if self.xb_user_username == "":
            if DEBUG: logger.error('SWPWRXBlock self.xb_user_username was empty')
            self.xb_user_username = 'FIXME'
        self.xb_user_fullname = xb_user.full_name
        if self.xb_user_fullname is None:
            if DEBUG: logger.error('SWPWRXBlock self.xb_user_fullname was None')
            self.xb_user_fullname = 'FIXME FIXME'
        if self.xb_user_fullname == "":
            if DEBUG: logger.error('SWPWRXBlock self.xb_user_fullname was empty')
            self.xb_user_fullname = 'FIXME FIXME'
        if DEBUG: logger.info('SWPWRXBlock student_view() self.xb_user_username: {e} self.xb_user_fullname: {f}'.format(e=self.xb_user_username,f=self.xb_user_fullname))

        # Determine which stepwise variant to use

        self.variants_count = 1

        if DEBUG: logger.info("SWPWRXBlock student_view() self.variants_count={c}".format(c=self.variants_count))
        # Pick a variant at random, and make sure that it is one we haven't attempted before.

        random.seed()				# Use the clock to seed the random number generator for picking variants
        self.question = self.pick_variant()

        # question = self.question		# Don't need local var
        q_index = self.question['q_index']

        if DEBUG: logger.info("SWPWRXBlock student_view() pick_variant selected q_index={i} question={q}".format(i=q_index,q=self.question))

### HEAD ASSETS
# <!DOCTYPE html>
# <html lang="en">
#   <head>
#     <meta charset="utf-8" />
#     <link rel="icon" href="/favicon.ico" />
#     <meta name="viewport" content="width=device-width, initial-scale=1" />
#     <meta name="theme-color" content="#000000" />
#     <meta
#       name="description"
#       content="Web site created using create-react-app"
#     />
#     <link rel="apple-touch-icon" href="/logo192.png" />
#     <!--
#       manifest.json provides metadata used when your web app is installed on a
#       user's mobile device or desktop. See https://developers.google.com/web/fundamentals/web-app-manifest/
#     -->
#     <link rel="manifest" href="/manifest.json" />
#
#     <title>Querium StepWise Power</title>
#
#     <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js"></script>
#     <script src="https://stepwise.querium.com/libs/mathquill/mathquill.js"></script>
#
#     <!-- #### START OF STEPWISE STUFF #### -->
#     <link
#       rel="stylesheet"
#       id="options_typography_Open+Sans:400,700-css"
#       href="https://fonts.googleapis.com/css?family=Open+Sans:400,700"
#       type="text/css"
#       media="all"
#     />
#     <link
#       rel="stylesheet"
#       id="options_typography_Lato:300,900-css"
#       href="https://fonts.googleapis.com/css?family=Lato:300,900"
#       type="text/css"
#       media="all"
#     />
#
#     <!-- HTML5 Shim and Respond.js IE8 support of HTML5 elements and media queries -->
#     <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
#     <!--[if lt IE 9]>
#       <script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
#       <script src="https://oss.maxcdn.com/libs/respond.js/1.4.2/respond.min.js"></script>
#     <![endif]-->
#
#     <!-- MathJax is required as is support for Latex, MathML and ASCIIMath -->
#     <script
#       type="text/javascript"
#       async
#       src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.0/MathJax.js?config=TeX-MML-AM_HTMLorMML"
#     ></script>
#     <script type="text/x-mathjax-config">
#       MathJax.Hub.Config({ messageStyle: 'none', skipStartupTypeset: true, showMathMenu: true, tex2jax: { preview: 'none' }, asciimath2jax: { delimiters: [['`','`'],['``','``']], preview: "none" }, AsciiMath: {displaystyle: false} }); MathJax.Hub.Register.LoadHook("[MathJax]/extensions/asciimath2jax.js",function () { var AM = MathJax.Extension.asciimath2jax, CREATEPATTERNS = AM.createPatterns; AM.createPatterns = function () { var result = CREATEPATTERNS.call(this); this.match['``'].mode = ";mode=display"; return result; }; }); MathJax.Hub.Register.StartupHook("AsciiMath Jax Ready",function () { var AM = MathJax.InputJax.AsciiMath; AM.postfilterHooks.Add(function (data) { if (data.script.type.match(/;mode=display/)) {data.math.root.display = "block"} return data; }); });
#     </script>
#
#     <link
#       rel="stylesheet"
#       type="text/css"
#       media="screen"
#       href="https://code.ionicframework.com/ionicons/2.0.1/css/ionicons.min.css"
#     />

#     <script type="text/javascript">
#       function getInternetExplorerVersion() {
#         // Returns the version of Internet Explorer or a -1 (indicating the use of another browser).
#         var rv = -1; // Return value assumes failure.
#         if (navigator.appName == "Microsoft Internet Explorer") {
#           var ua = navigator.userAgent;
#           var re = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})");
#           if (re.exec(ua) != null) {
#             rv = parseFloat(RegExp.$1);
#           }
#         }
#         return rv;
#       }
#
#       var ieVer = getInternetExplorerVersion();
#       if (ieVer > 2 && ieVer < 10) {
#         alert(
#           "Sorry, you are using an obsolete version of Internet Explorer. Querium has been designed for the secure, modern web.  Querium joins Microsoft in encouraging you to upgrade to Internet Explorer 10 or 11."
#         );
#         window.open(
#           "http://blogs.msdn.com/b/ie/archive/2014/08/07/stay-up-to-date-with-internet-explorer.aspx",
#           "_self"
#         );
#       }
#     </script>
#
#     <!-- Loads the Lato font used by default in the StepWise UI. Can be     -->
#     <!-- overridden with a cascaded style sheet                             -->
#     <link
#       href="https://fonts.googleapis.com/css?family=Lato"
#       rel="stylesheet"
#     />
#     <link
#       href="https://fonts.googleapis.com/css?family=Oswald"
#       rel="stylesheet"
#     />
#
#     <!-- REQUIRED CSS files for Querium StepWise Client                     -->
#     <link
#       rel="stylesheet"
#       type="text/css"
#       href="https://stepwise.querium.com/libs/mathquill/mathquill.css"
#     />
#     <!-- REQUIRED for the chip components -->
#     <link
#       rel="stylesheet"
#       href="https://cdn.jsdelivr.net/gh/mlaursen/react-md@5.1.4/themes/react-md.teal-pink-200-light.min.css"
#     />
#     <link
#       rel="stylesheet"
#       type="text/css"
#       href="https://stepwise.querium.com/client/querium-stepwise-1.6.8.css"
#     />
#
#     <!-- REQUIRED Javascript files for Querium StepWise Client -->
#     <script src="https://www.gstatic.com/firebasejs/4.4.0/firebase.js"></script>
#     <script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular.min.js"></script>
#     <script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-sanitize.min.js"></script>
#     <script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-animate.min.js"></script>
#
#     <script
#       type="text/javascript"
#       src="https://stepwise.querium.com/client/querium-stepwise-1.6.8.1-sw4wp.js"
#     ></script>
#
#     <!-- Set this to true to enable logging -->
#     <script>
#       querium.qEvalLogging = true;
#     </script>
#
#     <!-- #### END OF STEPWISE STUFF #### -->
#   </head>
###

# Build content programatticaly that looks like the above HTML

        # NOTE: The following page now includes the script tag that loads the module for the main React app
        html = self.resource_string("static/html/swpwrxstudent.html")
        frag = Fragment(html.format(self=self))

        ### index.html assets
        # <html lang="en">
        #   <head>
        #     <meta charset="UTF-8" />
        #     <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
        #     <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
        #     <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
        #     <link rel="manifest" href="/site.webmanifest" />
        #     <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        #     <link rel="preconnect" href="https://fonts.googleapis.com" />
        #
        #     <link rel="preconnect" href="https://fonts.googleapis.com" />
        #     <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        #     <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=Irish+Grover&family=Sura:wght@400;700&display=swap" rel="stylesheet" />
        #
        #     <title>StepWise Power</title>
        #   </head>
        #   <body>
        #     <div id="root"></div>
        #     <script type="module" src="/public/main.tsx"></script>
        #   </body>
        # </html>
        ####
        frag.add_resource('<meta charset="UTF-8"/>','text/html','head')
        frag.add_resource('<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />','text/html','head')
        frag.add_resource('<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />','text/html','head')
        frag.add_resource('<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />','text/html','head')
        # Don't add site.webmanifest to eliminate 404 error since we need to give a deep path in the xblock static assets on the LMS server
        # frag.add_resource('<link rel="manifest" href="/site.webmanifest" />','text/html','head')
        frag.add_resource('<meta name="viewport" content="width=device-width,initial-scale=1.0"/>','text/html','head')
        frag.add_resource('<link rel="preconnect" href="https://fonts.googleapis.com" />','text/html','head')
        frag.add_resource('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />','text/html','head')
        frag.add_resource('<link href="https://fonts.googleapis.com/css2?family=Capriola&family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&family=Irish+Grover&display=swap" rel="stylesheet" />','text/html','head')
        frag.add_resource('<title>Querium StepWise Power</title>','text/html','head')
        # root div is in swpwrxstudent.html
        # html_string = '<div id="root"></div>'
        # frag.add_content(html_string)

        # resource_string = self.resource_string("public/assets/app.js")
        # if DEBUG: logger.info('SWPWRXBlock student_view() KENT example resource_string={r}'.format(r=resource_string))
        # Force a script tag of module type to hold the main React app file
        # html_string = '<script type="module" src="public/index-YyiH-LRh.js"></script>'
        # frag.add_content(html_string)

# Apparently jQuery already loaded
#HIDEME        frag.add_javascript_url("//ajax.googleapis.com/ajax/libs/jquery/1.11.0/jquery.min.js")
#NOTYET        frag.add_javascript_url("//stepwise.querium.com/libs/mathquill/mathquill.js")
#NOTYET        frag.add_css_url("//fonts.googleapis.com/css?family=Open+Sans:400,700")
#NOTYET        frag.add_css_url("//fonts.googleapis.com/css?family=Lato:300,900")
#NOTYET         <!-- HTML5 Shim and Respond.js IE8 support of HTML5 elements and media queries -->
#NOTYET     <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
#NOTYET     <!--[if lt IE 9]>
#NOTYET       <script src="https://oss.maxcdn.com/libs/html5shiv/3.7.0/html5shiv.js"></script>
#NOTYET       <script src="https://oss.maxcdn.com/libs/respond.js/1.4.2/respond.min.js"></script>
#NOTYET     <![endif]-->
#                Bootstrap CSS
#NOTYET        frag.add_javascript_url("//cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.0/MathJax.js?config=TeX-MML-AM_HTMLorMML")
#NOTYET        frag.add_resource('<script type="text/x-mathjax-config">MathJax.Hub.Config({ messageStyle: \'none\', skipStartupTypeset: true, showMathMenu: true, tex2jax: { preview: \'none\' }, asciimath2jax: { delimiters: [[\'`\',\'`\'],[\'``\',\'``\']], preview: "none" }, AsciiMath: {displaystyle: false} }); MathJax.Hub.Register.LoadHook("[MathJax]/extensions/asciimath2jax.js",function () { var AM = MathJax.Extension.asciimath2jax, CREATEPATTERNS = AM.createPatterns; AM.createPatterns = function () { var result = CREATEPATTERNS.call(this); this.match[\'``\'].mode = ";mode=display"; return result; }; }); MathJax.Hub.Register.StartupHook("AsciiMath Jax Ready",function () { var AM = MathJax.InputJax.AsciiMath; AM.postfilterHooks.Add(function (data) { if (data.script.type.match(/;mode=display/)) {data.math.root.display = "block"} return data; }); });</script>','text/html','head')
#NOTYET        frag.add_css_url("//code.ionicframework.com/ionicons/2.0.1/css/ionicons.min.css")
#NOTYET Don't include this for now.  Just running on iPads
#         frag.add_resource('<script type="text/javascript">function getInternetExplorerVersion(){var e=-1;if("Microsoft Internet Explorer"==navigator.appName){var r=navigator.userAgent;null!=new RegExp("MSIE ([0-9]{1,}[.0-9]{0,})").exec(r)&&(e=parseFloat(RegExp.$1))}return e}var ieVer=getInternetExplorerVersion();2<ieVer&&ieVer<10&&(alert("Sorry, you are using an obsolete version of Internet Explorer. Querium has been designed for the secure, modern web.  Querium joins Microsoft in encouraging you to upgrade to Internet Explorer 10 or 11."),window.open("http://blogs.msdn.com/b/ie/archive/2014/08/07/stay-up-to-date-with-internet-explorer.aspx","_self"))</script>','text/html','head')

#NOTYET        frag.add_css_url("//fonts.googleapis.com/css?family=Lato")
#NOTYET        frag.add_css_url("//fonts.googleapis.com/css?family=Oswald")
#NOTYET        frag.add_css_url("//stepwise.querium.com/libs/mathquill/mathquill.css")
#NOTYET        # <!-- REQUIRED for the chip components -->
#NOTYET        frag.add_css_url("//cdn.jsdelivr.net/gh/mlaursen/react-md@5.1.4/themes/react-md.teal-pink-200-light.min.css")
#NOTYET        frag.add_css_url("//stepwiseai.querium.com/client/querium-stepwise-1.6.8.1-sw4wp.css")
#NOTYET        frag.add_javascript_url("//www.gstatic.com/firebasejs/4.4.0/firebase.js")               # For qEval client-side logging
#NOTYET        frag.add_javascript_url("//ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular.min.js")
#NOTYET        frag.add_javascript_url("//ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-sanitize.min.js")
#NOTYET        frag.add_javascript_url("//ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-animate.min.js")
#NOTYET        frag.add_javascript_url("//stepwiseai.querium.com/client/querium-stepwise-1.6.8.1-sw4wp.js")

        frag.add_css(self.resource_string("static/css/swpwrxstudent.css"))
        frag.add_javascript(self.resource_string("static/js/src/swpwrxstudent.js"))

#WASIN2022        frag.add_content('<script>querium.qEvalLogging=true;</script>')

# Now we can finally add the React app bundle assets

#WASIN2022        frag.add_css(self.resource_string("public/assets/app.css"))

#NOTINJVR        frag.add_resource('<base href="/testq_assets/"/>','text/html','head')		# Needed so react code can find its pages. Don't do earlier or impacts relative pathnames of resources

        frag.add_javascript(self.resource_string("static/js/src/final_callback.js"))    # Final submit callback code and define swpwr_problems[]

        if (TEST_MODE):
            if DEBUG: logger.info("SWPWRXBlock student_view() TEST_MODE={e}".format(e=TEST_MODE))
            ###
            # Resources from index.html
            # <html lang="en">
            #   <head>
            #     <meta charset="UTF-8" />
            #     <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
            #     <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
            #     <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
            #     <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            #     <title>testReactxBlock</title>
            #     <script>
            #       window.swpwr = {
            #         options: {
            #           swapiUrl: "https://swapi2.onrender.com/",
            #           gltfUrl: "https://s3.amazonaws.com/stepwise-editorial.querium.com/swpwr/dist/models/",
            #         },
            #       };
            #     </script>
            #   </head>
            #   <body>
            #     <div id="root"></div>
            #     <script type="module" src="/public/main.tsx"></script>
            #   </body>
            # </html>
            ###
            # frag.add_resource('<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png"/>','text/html','head')
            # frag.add_resource('<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png"/>','text/html','head')
            # frag.add_resource('<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png"/>','text/html','head')
            # frag.add_resource('<meta name="viewport" content="width=device-width, initial-scale=1.0" />','text/html','head')
            ### FIXME: have to add the problem and student fields to the snippet_string
            # mid_string = '$(function() {'+snippet_string     # Add jQuery function start
            # final_string = mid_string+'});'                 # Adds final '});' for the jQuery function
            # frag.add_resource(final_string,'application/javascript','foot')
            frag.add_javascript_url("//s3.amazonaws.com/stepwise-editorial.querium.com/swpwr/dist/assets/index-CIesktn4.js")
            # html_string = '<div id="root"></div>'
            # frag.add_content(html_string)
        else:
            # Invalid schema choices should be a CSV list of one or more of these: "TOTAL", "DIFFERENCE", "CHANGEINCREASE", "CHANGEDECREASE", "EQUALGROUPS", and "COMPARE"
            # Invalid schema choices can also be the official names: "additiveTotalSchema", "additiveDifferenceSchema", "additiveChangeSchema", "subtractiveChangeSchema", "multiplicativeEqualGroupsSchema", and "multiplicativeCompareSchema"
            # Convert the upper-case names to the 'official' names. NB: The order of .replace() calls might matter if one of these schema names is a substring of another name.
            invalid_schemas_js = self.q_swpwr_invalid_schemas
            if DEBUG: logger.info("SWPWRXBlock student_view() before mapping loop invalid_schemas_js={e}".format(e=invalid_schemas_js))
            mapping = { "TOTAL":"additiveTotalSchema", "DIFFERENCE":"additiveDifferenceSchema", "CHANGEINCREASE":"additiveChangeSchema", "CHANGEDECREASE":"subtractiveChangeSchema", "EQUALGROUPS":"multiplicativeEqualGroupsSchema", "COMPARE":"multiplicativeCompareSchema" }
            for schema_key, schema_value in mapping.items():
                invalid_schemas_js = invalid_schemas_js.replace(schema_key, schema_value)
                if DEBUG: logger.info("SWPWRXBlock student_view() in mapping loop schema_key={k} schema_value={v} invalid_schemas_js={e}".format(k=schema_key,v=schema_value,e=invalid_schemas_js))

            swpwr_string = 'window.swpwr = {' + \
                           '    options: {' + \
                           '        swapiUrl: "https://swapi2.onrender.com", ' + \
                           '        gltfUrl: "https://s3.amazonaws.com/stepwise-editorial.querium.com/swpwr/dist/models/", ' + \
                           '        rank: "' + self.q_swpwr_rank + '", ' + \
                           '        disabledSchemas: "' + invalid_schemas_js + '"' + \
                           '    }, ' + \
                           '    student: { ' + \
                           '        studentId: "' + self.xb_user_username + '", ' + \
                           '        fullName: "' + self.xb_user_fullname + '", ' + \
                           '        familiarName: "' + 'NONE' + '"' + \
                           '    },' + \
                           '    problem: { ' + \
                           '        appKey: "' + self.q_grade_app_key + '", ' + \
                           '        policyId: "' + '$A9$' + '", ' + \
                           '        problemId: "' + self.q_id + '", ' + \
                           '        title: "' + 'SAMPLE' + '", ' + \
                           '        stimulus: \'' + str(self.q_stimulus).replace('\'', '&apos;') + '\', ' + \
                           '        topic: "' + 'gradeBasicAlgebra' + '", ' + \
                           '        definition: \'' + str(self.q_definition).replace('\'', '&apos;') + '\', ' + \
			   '        wpHintsString: \'' + str(self.q_swpwr_problem_hints).replace('\'', '&apos;') + '\', ' + \
                           '        mathHints: [' + \
                           '                   "' + str(self.q_hint1).replace('\'', '&apos;').replace('\"', '&quot;') + '",' + \
                           '                   "' + str(self.q_hint2).replace('\'', '&apos;').replace('\"', '&quot;') + '",' + \
                           '                   "' + str(self.q_hint3).replace('\'', '&apos;').replace('\"', '&quot;') + '"' + \
                           '                   ]' + \
                           '    },' + \
                           '    handlers: {' + \
                           '        onComplete: (session,log) => {' + \
                           '            console.info("onComplete session",session);' + \
                           '            console.info("onComplete log",log);' + \
                           '            console.info("onComplete handlerUrlSwpwrFinalResults",handlerUrlSwpwrFinalResults);' + \
                           '            const solution = [session,log];' + \
                           '            var solution_string = JSON.stringify(solution);' + \
                           '            console.info("onComplete solution_string",solution_string);' + \
                           '            $.ajax({' + \
                           '                type: "POST",' + \
                           '                url: handlerUrlSwpwrFinalResults,' + \
                           '                data: solution_string,' + \
                           '                success: function (data,msg) {' + \
                           '                    console.info("onComplete solution POST success");' + \
                           '                    console.info("onComplete solution POST data",data);' + \
                           '                    console.info("onComplete solution POST msg",msg);' + \
                           '                },' + \
                           '                error: function(XMLHttpRequest, textStatus, errorThrown) {' + \
                           '                    console.info("onComplete solution POST error textStatus=",textStatus," errorThrown=",errorThrown);' + \
                           '                }' + \
                           '            });' + \
                           '            $(\'.problem-complete\').show();' + \
                           '            $(\'.unit-navigation\').show();' + \
                           '        },' + \
                           '        onStep: (session,log) => {' + \
                           '            console.info("onStep session",session);' + \
                           '            console.info("onStep log",log);' + \
                           '            console.info("onStep handlerUrlSwpwrPartialResults",handlerUrlSwpwrPartialResults);' + \
                           '            const solution = [session,log];' + \
                           '            var solution_string = JSON.stringify(solution);' + \
                           '            console.info("onStep solution_string",solution_string);' + \
                           '            $.ajax({' + \
                           '                type: "POST",' + \
                           '                url: handlerUrlSwpwrPartialResults,' + \
                           '                data: solution_string,' + \
                           '                success: function (data,msg) {' + \
                           '                    console.info("onStep solution POST success");' + \
                           '                    console.info("onStep solution POST data",data);' + \
                           '                    console.info("onStep solution POST msg",msg);' + \
                           '                },' + \
                           '                error: function(XMLHttpRequest, textStatus, errorThrown) {' + \
                           '                    console.info("onStep solution POST error textStatus=",textStatus," errorThrown=",errorThrown);' + \
                           '                }' + \
                           '            });' + \
                           '        }' + \
                           '    }' + \
                           '};' + \
                           'try { ' + \
                           '    console.log( "before JSON.parse wpHintsString ",window.swpwr.problem.wpHintsString);' + \
                           '    window.swpwr.problem.wpHints = JSON.parse(window.swpwr.problem.wpHintsString);' + \
                           '    console.log( "wpHints data is ",window.swpwr.problem.wpHints );' + \
                           '} catch(e) {' + \
                           '    console.log( "Could not decode wpHints string",e.message );' + \
                           '};'
            if DEBUG: logger.info("SWPWRXBlock student_view() swpwr_string={e}".format(e=swpwr_string))
            frag.add_resource(swpwr_string,'application/javascript','foot')
            # Emit the Python dict into the HTML as Javascript object
            # json_string = json.dumps(swpwr_problem_template,separators=(',', ':'))
            # javascript_string = '      window.swpwr_problem_template = '+json_string+';'
            # javascript_string = javascript_string+'window.swpwr_problems.push(window.swpwr_problem_template);console.info("window.swpwr_problems.length=",window.swpwr_problems.length);'
            # if DEBUG: logger.info("SWPWRXBlock student_view() swpwr_problem_template final javascript={j}".format(j=javascript_string))
            # frag.add_javascript(javascript_string)     # SWPWR problem to work.

            # Load up the React app bundle js, and wrap it as needed so it does not run until after the DOM is completely loaded
            # bundle_string = self.resource_string("public/assets/app.js")

            # if DEBUG: logger.info("SWPWRXBlock student_view() bundle_string head={e}".format(e=bundle_string[0:100]))
            # if DEBUG: logger.info("SWPWRXBlock student_view() bundle_string tail={e}".format(e=bundle_string[len(bundle_string)-100:]))
            # # Wrap the bundle js in a jQuery function so it runs after the DOM finishes loading, to emulate the 'defer' action of a <script> tag in the React index.html
            # mid_string = '$(function() {'+bundle_string     # Add jQuery function start
            # if DEBUG: logger.info("SWPWRXBlock student_view() mid_string head={e}".format(e=mid_string[0:100]))
            # if DEBUG: logger.info("SWPWRXBlock student_view() mid_string tail={e}".format(e=mid_string[len(mid_string)-100:]))
            # # Add jQuery function ending.
            # final_string = mid_string+'});'                 # Adds final '});' for the jQuery function
            # if DEBUG: logger.info("SWPWRXBlock student_view() final_string head={e}".format(e=final_string[0:100]))
            # if DEBUG: logger.info("SWPWRXBlock student_view() final_string tail={e}".format(e=final_string[len(final_string)-100:]))
            # frag.add_javascript_url("//s3.amazonaws.com/stepwise-editorial.querium.com/swpwr/public/index-YyiH-LRh.js")  # This gets a CORB error
            # frag.add_javascript_url("public/index-YyiH-LRh.js") # Need to update any time swpwr gets rebuilt
            # frag.add_javascript(self.resource_string("public/index-YyiH-LRh.js")) # Need to update any time swpwr gets rebuilt
            # This script module apparently cannot be generated using the Fragment library, so we'll next try hard coding it into the page template.
            # frag.add_resource('<script type="module" src="/public/index-YyiH-LRh.js"></script>','application/javascript','head')
            # frag.add_resource(final_string,'application/javascript','foot')

        frag.initialize_js('SWPWRXStudent', {})  # Call the entry point
        return frag


    # PUBLISH_GRADE
    # For rescoring events
    def publish_grade(self):
        if DEBUG: logger.info("SWPWRXBlock publish_grade() pretrimmed self.raw_earned={e} self.weight={w}".format(e=self.raw_earned,w=self.weight))
        if self.raw_earned < 0.0:
           self.raw_earned = 0.0
        if self.raw_earned > self.weight:
           self.raw_earned = self.weight
        if DEBUG: logger.info("SWPWRXBlock publish_grade() posttrimmed self.raw_earned={e} self.weight={w}".format(e=self.raw_earned,w=self.weight))
        self.runtime.publish(self, 'grade',
             {   'value': self.raw_earned*1.0,
                 'max_value': self.weight*1.0
             })


    # SAVE
    def save(self):
        if DEBUG: logger.info("SWPWRXBlock save() self{s}".format(s=self))
        # If we don't have a url_name for this xblock defined to make the xblock unique, assign ourselves a unique UUID4 as a hex string.
        # Otherwise course imports can confuse multiple swpwrxblocks with url_name == "NONE" (the default)
        # We don't currently allow authors to specify a value for this field in studio since we don't want to burden them with assigning UUIDs.
        # There was also a long period of time prior to September 2024 where we didn't assign any value to this field, so we try to catch
        # such swpwrxblocks and correct this at the time of the next save()
        try:
            self.url_name
        except NameError as e:
            logger.info('SWPWRXBlock save() self.url_name was undefined: {e}'.format(e=e))
            self.url_name = 'NONE'
        if self.url_name == '' or self.url_name == "NONE":
            self.url_name = str(uuid.uuid4().hex)
            if DEBUG: logger.info('SWPWRXBlock save() defined self.url_name as {s}'.format(s=self.url_name))
        else:
            if DEBUG: logger.info('SWPWRXBlock save() there is an existing url_name {s}'.format(s=self.url_name))
        # if we managed to store a two-element list in the solution Dict, fix it
        if isinstance(self.solution, list):
	    my_dict['session'] = self.solution[0]
            if len(self.solution) > 1:
	        my_dict['log'] = self.solution[1]
            else:
                my_dict['log'] = []
	    self.solution = my_dict
            logger.info('SWPWRXBlock save() solution converted list to Dict: {e}'.format(e=self.solution))
        try:
            XBlock.save(self)       # Call parent class save()
        # except (NameError,AttributeError,InvalidScopeError) as e:
        except Exception as e:
            logger.info('SWPWRXBlock save() had an error: {e}'.format(e=e))
        if DEBUG: logger.info("SWPWRXBlock save() back from parent save. self.solution={s}".format(s=self.solution))


    # GET_DATA: RETURN DATA FOR THIS QUESTION
    @XBlock.json_handler
    def get_data(self, msg, suffix=''):
        if DEBUG: logger.info("SWPWRXBlock get_data() entered. msg={msg}".format(msg=msg))

        if self.my_max_attempts is None:
            self.my_max_attempts = -1

        if DEBUG: logger.info("SWPWRXBlock get_data() self.solution={a}".format(a=self.solution))

        # NOTE: swpwr app does not need to be passed the solution
        #       to our previous attempt at this problem
        data = {
            "question" : self.question,
            "grade" : self.grade,
            "solution" : {},
            "count_attempts" : self.count_attempts,
            "variants_count" : self.variants_count,
            "max_attempts" : self.my_max_attempts
        }
        if DEBUG: logger.info("SWPWRXBlock get_data() data={d}".format(d=data))
        json_data = json.dumps(data)
        return json_data

    # SAVE GRADE
    ### @XBlock.json_handler	# We're just calling it directly now, not in a callback.
    def save_grade(self, data, suffix=''):
        if DEBUG: logger.info('SWPWRXBlock save_grade() entered')
        if DEBUG: logger.info("SWPWRXBlock save_grade() self.max_attempts={a}".format(a=self.max_attempts))

        # Check for missing grading attributes

        if DEBUG: logger.info("SWPWRXBlock save_grade() initial self={a}".format(a=self))
        if DEBUG: logger.info("SWPWRXBlock save_grade() initial data={a}".format(a=data))

        try: swpwr_results = self.swpwr_results
        except (NameError,AttributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.swpwr_results was not defined: {e}'.format(e=e))
             swpwr_results = ""

        try: q_weight = self.q_weight
        except (NameError,AttributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.q_weight was not defined: {e}'.format(e=e))
             q_weight = 1.0

        try: q_grade_showme_ded = self.q_grade_showme_ded
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.q_grade_showme_dev was not defined: {e}'.format(e=e))
             q_grade_showme_ded = -1

        try: q_grade_hints_count = self.q_grade_hints_count
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.q_grade_hints_count was not defined: {e}',format(e=e))
             q_grade_hints_count = -1

        try: q_grade_hints_ded = self.q_grade_hints_ded
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.q_grade_hints_ded was not defined: {e}'.format(e=e))
             q_grade_hints_ded = -1

        try: q_grade_errors_count = self.q_grade_errors_count
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.q_grade_errors_count was not defined: {e}'.format(e=e))
             q_grade_errors_count = -1

        try: q_grade_errors_ded = self.q_grade_errors_ded
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.q_grade_errors_ded was not defined: {e}'.format(e=e))
             q_grade_errors_ded = -1

        try: q_grade_min_steps_count = self.q_grade_min_steps_count
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.q_grade_min_steps_count was not defined: {e}'.format(e=e))
             q_grade_min_steps_count = -1

        try: q_grade_min_steps_ded = self.q_grade_min_steps_ded
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.q_grade_min_steps_ded was not defined: {e}'.format(e=e))
             q_grade_min_steps_ded = -1

        try: q_grade_app_key = self.q_grade_app_key
        except (NameError,AtrributeError) as e:
             if DEBUG: logger.info('SWPWRXBlock save_grade() self.q_grade_app_key was not defined: {e}'.format(e=e))
             q_grade_app_key = "SBIRPhase2"

        # Apply grading defaults

        if q_weight == -1:
            if DEBUG: logger.info('SWPWRXBlock save_grade() weight set to 1.0')
            q_weight = 1.0
        if q_grade_showme_ded == -1:
            if DEBUG: logger.info('SWPWRXBlock save_grade() showme default set to 3.0')
            q_grade_showme_ded = 3.0
        if q_grade_hints_count == -1:
            if DEBUG: logger.info('SWPWRXBlock save_grade() hints_count default set to 2')
            q_grade_hints_count = 2
        if q_grade_hints_ded == -1:
            if DEBUG: logger.info('SWPWRXBlock save_grade() hints_ded default set to 1.0')
            q_grade_hints_ded = 1.0
        if q_grade_errors_count == -1:
            if DEBUG: logger.info('SWPWRXBlock save_grade() errors_count default set to 3')
            q_grade_errors_count = 3
        if q_grade_errors_ded == -1:
            if DEBUG: logger.info('SWPWRXBlock save_grade() errors_ded default set to 1.0')
            q_grade_errors_ded = 1.0
        if q_grade_min_steps_ded == -1:
            if DEBUG: logger.info('SWPWRXBlock save_grade() min_steps_ded default set to 0.25')
            q_grade_min_steps_ded = 0.25
        if q_grade_app_key == "":
            if DEBUG: logger.info('SWPWRXBlock save_grade() app_key default set to SBIRPhase2')
            q_grade_app_key = "SBIRPhase2"

#
# NOTE: Don't count min_steps on the POWER xblock
#         """
#         Count the total number of VALID steps the student input.
#         Used to determine if they get full credit for entering at least a min number of good steps.
#         """
#         valid_steps = 0
#         if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps data={d}".format(d=data))
#         step_details = data['stepDetails']
#         if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps step_details={d}".format(d=step_details))
#         if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps len(step_details)={l}".format(l=len(step_details)))
#         for c in range(len(step_details)):
#             if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps begin examine step c={c} step_details[c]={d}".format(c=c,d=step_details[c]))
#             for i in range (len(step_details[c]['info'])):
#                 if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps examine step c={c} i={i} step_details[c]['info']={s}".format(c=c,i=i,s=step_details[c]['info']))
#                 if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps examine step c={c} i={i} step_details[c]['info'][i]={s}".format(c=c,i=i,s=step_details[c]['info'][i]))
#                 step_status = step_details[c]['info'][i]['status']
#                 if (step_status == 0):       # victory valid_steps += 1
#                     valid_steps += 1
#                     if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps c={c} i={i} victory step found".format(c=c,i=i))
#                 elif (step_status == 1):     # valid step
#                     valid_steps += 1
#                     if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps c={c} i={i} valid step found".format(c=c,i=i))
#                 elif (step_status == 3):     # invalid step
#                     valid_steps += 0         # don't count invalid steps
#                 else:
#                     if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps c={c} i={i} ignoring step_status={s}".format(c=c,i=i,s=step_status))
#                 if DEBUG: logger.info("SWPWRXBlock save_grade() count valid_steps examine step c={c} i={i} step_status={s} valid_steps={v}".format(c=c,i=i,s=step_status,v=valid_steps))
#         if DEBUG: logger.info("SWPWRXBlock save_grade() final valid_steps={v}".format(v=valid_steps))
#
#         grade=3.0
#         max_grade=grade

        # Track whether they've completed it or not and assign 1.0 points if they have completed the problem
        if self.is_answered:
            grade=1.0
        else:
            grade=0.0
        max_grade=1.0

#
# NOTE: Don't count the number of errors in the swpwrxblock
#
#         if DEBUG: logger.info('SWPWRXBlock save_grade() initial grade={a} errors={b} errors_count={c} hints={d} hints_count={e} showme={f} min_steps={g} valid_steps={h}'.format(a=grade,b=data['errors'],c=q_grade_errors_count,d=data['hints'],e=q_grade_hints_count,f=data['usedShowMe'],g=q_grade_min_steps_count,h=valid_steps))
#         if data['errors']>q_grade_errors_count:
#             grade=grade-q_grade_errors_ded
#             if DEBUG: logger.info('SWPWRXBlock save_grade() errors test errors_ded={a} grade={b}'.format(a=q_grade_errors_ded,b=grade))
#         if data['hints']>q_grade_hints_count:
#             grade=grade-q_grade_hints_ded
#             if DEBUG: logger.info('SWPWRXBlock save_grade() hints test hints_ded={a} grade={b}'.format(a=q_grade_hints_ded,b=grade))
#         if data['usedShowMe']:
#             grade=grade-q_grade_showme_ded
#             if DEBUG: logger.info('SWPWRXBlock save_grade() showme test showme_ded={a} grade={b}'.format(a=q_grade_showme_ded,b=grade))
#
#         # Don't subtract min_steps points on a MatchSpec problem or DomainOf
#         self.my_q_definition = data['answered_question']['q_definition']
#         if DEBUG: logger.info('SWPWRXBlock save_grade() check on min_steps deduction grade={g} max_grade={m} q_grade_min_steps_count={c} q_grade_min_steps_ded={d} self.my_q_definition={q} self.q_grade_app_key={k}'.format(g=grade,m=max_grade,c=q_grade_min_steps_count,d=q_grade_min_steps_ded,q=self.my_q_definition,k=self.q_grade_app_key))
#         if (grade >= max_grade and valid_steps < q_grade_min_steps_count and self.my_q_definition.count('MatchSpec') == 0 and self.my_q_definition.count('DomainOf') == 0 ):
#             grade=grade-q_grade_min_steps_ded
#             if DEBUG: logger.info('SWPWRXBlock save_grade() took min_steps deduction after grade={g}'.format(g=grade))
#         else:
#             if DEBUG: logger.info('SWPWRXBlock save_grade() did not take min_steps deduction after grade={g}'.format(g=grade))
#
#         if grade<0.0:
#             logger.info('SWPWRXBlock save_grade() zero negative grade')
#             grade=0.0
#
#         if DEBUG: logger.info("SWPWRXBlock save_grade() final grade={a} q_weight={b}".format(a=grade,b=q_weight))

        # The following now handled below by publish_grade() after save() is complete:
        # self.runtime.publish(self, 'grade',
        #     {   'value': (grade/3.0)*weight,
        #         'max_value': 1.0*weight
        #     })

# NOTE: Don't assume 3 points per problem in swpwrxblock
#         self.raw_earned = (grade/3.0)*weight
        self.raw_earned = grade

        if DEBUG: logger.info("SWPWRXBlock save_grade() raw_earned={a}".format(a=self.raw_earned))

        if DEBUG: logger.info("SWPWRXBlock save_grade() final data={a}".format(a=data))
        self.solution = data
        if DEBUG: logger.info("SWPWRXBlock save_grade() final self.solution={a}".format(a=self.solution))
        self.grade = grade
        if DEBUG: logger.info("SWPWRXBlock save_grade() grade={a}".format(a=self.grade))

        # Don't increment attempts on save grade.  We want to increment them when the student starts
        # a question, not when they finish.  Otherwise people can start the question as many times
        # as they want as long as they don't finish it, then reload the page.
        # self.count_attempts += 1
        # make sure we've recorded this atttempt, but it should have been done in start_attempt():
        try:
            if self.q_index != -1:
                self.variants_attempted = set.bit_set_one(self.variants_attempted,self.q_index)
                if DEBUG: logger.info("SWPWRXBlock save_grade() record variants_attempted for variant {a}".format(v=self.q_index))
                self.previous_variant = self.q_index
                if DEBUG: logger.info("SWPWRXBlock save_grade() record previous_variant for variant {a}".format(v=self.previous_variant))
            else:
                if DEBUG: logger.error("SWPWRXBlock save_grade record variants_attempted for variant -1")
        except (NameError,AttributeError) as e:
            if DEBUG: logger.warning('SWPWRXBlock save_grade() self.q_index was not defined: {e}'.format(e=e))

        self.save()     # Time to persist our state!!!

        self.publish_grade()     # Now publish our grade results to persist them into the grading database

        # if DEBUG: logger.info("SWPWRXBlock save_grade() final self={a}".format(a=self))
        if DEBUG: logger.info("SWPWRXBlock save_grade() final self.count_attempts={a}".format(a=self.count_attempts))
        if DEBUG: logger.info("SWPWRXBlock save_grade() final self.solution={a}".format(a=self.solution))
        if DEBUG: logger.info("SWPWRXBlock save_grade() final self.grade={a}".format(a=self.grade))
        if DEBUG: logger.info("SWPWRXBlock save_grade() final self.weight={a}".format(a=self.weight))
        if DEBUG: logger.info("SWPWRXBlock save_grade() final self.variants_attempted={v}".format(v=self.variants_attempted))
        if DEBUG: logger.info("SWPWRXBlock save_grade() final self.previous_variant={v}".format(v=self.previous_variant))



    # START ATTEMPT
    @XBlock.json_handler
    def start_attempt(self, data, suffix=''):
        if DEBUG: logger.info("SWPWRXBlock start_attempt() entered")
        if DEBUG: logger.info("SWPWRXBlock start_attempt() data={d}".format(d=data))
        if DEBUG: logger.info("SWPWRXBlock start_attempt() self.count_attempts={c} max_attempts={m}".format(c=self.count_attempts,m=self.max_attempts))
        if DEBUG: logger.info("SWPWRXBlock start_attempt() self.variants_attempted={v}".format(v=self.variants_attempted))
        if DEBUG: logger.info("SWPWRXBlock start_attempt() self.previous_variant={v}".format(v=self.previous_variant))
        # logger.info("SWPWRXBlock start_attempt() action={d} sessionId={s} timeMark={t}".format(d=data['status']['action'],s=data['status']['sessionId'],t=data['status']['timeMark']))
        if DEBUG: logger.info("SWPWRXBlock start_attempt() passed q_index={q}".format(q=data['q_index']))
        self.count_attempts += 1
        if DEBUG: logger.info("SWPWRXBlock start_attempt() updated self.count_attempts={c}".format(c=self.count_attempts))
        variant = data['q_index']
        if DEBUG: logger.info("variant is {v}".format(v=variant))
        if self.bit_is_set(self.variants_attempted,variant):
            if DEBUG: logger.info("variant {v} has already been attempted!".format(v=variant))
        else:
            if DEBUG: logger.info("adding variant {v} to self.variants_attempted={s}".format(v=variant,s=self.variants_attempted))
            self.variants_attempted = self.bit_set_one(self.variants_attempted,variant)
            if DEBUG: logger.info("checking bit_is_set {v}={b}".format(v=variant,b=self.bit_is_set(self.variants_attempted,variant)))
            self.previous_variant = variant
            if DEBUG: logger.info("setting previous_variant to {v}".format(v=variant))
            
        return_data = {
            "count_attempts" : self.count_attempts,
        }
        if DEBUG: logger.info("SWPWRXBlock start_attempt() done return_data={return_data}".format(return_data=return_data))
        json_data = json.dumps(return_data)
        return json_data


    # RESET: PICK A NEW VARIANT
    @XBlock.json_handler
    def retry(self, data, suffix=''):
        if DEBUG: logger.info("SWPWRXBlock retry() entered")
        if DEBUG: logger.info("SWPWRXBlock retry() data={d}".format(d=data))
        if DEBUG: logger.info("SWPWRXBlock retry() self.count_attempts={c} max_attempts={m}".format(c=self.count_attempts,m=self.max_attempts))
        if DEBUG: logger.info("SWPWRXBlock retry() self.variants_attempted={v}".format(v=self.variants_attempted))
        if DEBUG: logger.info("SWPWRXBlock retry() pre-pick_question q_index={i}".format(v=self.question['q_index']))
        self.question = self.pick_variant()

        return_data = {
            "question" : self.question,
        }

        if DEBUG: logger.info("SWPWRXBlock retry() post-pick returning self.question={q} return_data={r}".format(q=self.question,r=return_data))
        json_data = json.dumps(return_data)
        return json_data


    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        if DEBUG: logger.info('SWPWRXBlock workbench_scenarios() entered')
        """A canned scenario for display in the workbench."""
        return [
            ("SWPWRXBlock",
             """<swpwrxblock/>
             """),
            ("Multiple SWPWRXBlock",
             """<vertical_demo>
                <swpwrxblock/>
                <swpwrxblock/>
                <swpwrxblock/>
                </vertical_demo>
             """),
        ]


    def studio_view(self, context=None):
        if DEBUG: logger.info('SWPWRXBlock studio_view() entered.')
        """
        The STUDIO view of the SWPWRXBlock, shown to instructors
        when authoring courses.
        """
        html = self.resource_string("static/html/swpwrxstudio.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/swpwrxstudio.css"))
        frag.add_javascript(self.resource_string("static/js/src/swpwrxstudio.js"))

        frag.initialize_js('SWPWRXStudio')
        return frag


    def author_view(self, context=None):
        if DEBUG: logger.info('SWPWRXBlock author_view() entered')
        """
        The AUTHOR view of the SWPWRXBlock, shown to instructors
        when previewing courses.
        """
        html = self.resource_string("static/html/swpwrxauthor.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/swpwrxauthor.css"))
        frag.add_javascript_url("//cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/MathJax.js?config=TeX-MML-AM_HTMLorMML")
        frag.add_javascript(self.resource_string("static/js/src/swpwrxauthor.js"))

        if DEBUG: logger.info("SWPWRXBlock SWPWRXAuthor author_view v={a}".format(a=self.q_definition))

        # tell author_view how many variants are defined
        variants = 1

        if DEBUG: logger.info("SWPWRXBlock SWPWRXAuthor author_view variants={a}".format(a=variants))

        frag.initialize_js('SWPWRXAuthor', variants)
        return frag


    # SAVE QUESTION
    @XBlock.json_handler
    def save_question(self, data, suffix=''):
        if DEBUG: logger.info('SWPWRXBlock save_question() entered')
        if DEBUG: logger.info('SWPWRXBlock save_question() data={d}'.format(d=data))
        self.q_max_attempts = int(data['q_max_attempts'])
        self.q_weight = float(data['q_weight'])
        if data['q_option_showme'].lower() == u'true':
            self.q_option_showme = True
        else:
            self.q_option_showme = False
        if data['q_option_hint'].lower() == u'true':
            self.q_option_hint = True
        else:
            self.q_option_hint = False
        self.q_grade_showme_ded = float(data['q_grade_showme_ded'])
        self.q_grade_hints_count = int(data['q_grade_hints_count'])
        self.q_grade_hints_ded = float(data['q_grade_hints_ded'])
        self.q_grade_errors_count = int(data['q_grade_errors_count'])
        self.q_grade_errors_ded = float(data['q_grade_errors_ded'])
        self.q_grade_min_steps_count = int(data['q_grade_min_steps_count'])
        self.q_grade_min_steps_ded = float(data['q_grade_min_steps_ded'])
        self.q_grade_app_key = str(data['q_grade_app_key'])

        self.q_id = data['id']
        self.q_label = data['label']
        self.q_stimulus = data['stimulus']
        self.q_definition = data['definition']
        self.q_type = data['qtype']
        self.q_display_math = data['display_math']
        self.q_hint1 = data['hint1']
        self.q_hint2 = data['hint2']
        self.q_hint3 = data['hint3']
        self.q_swpwr_problem = data['swpwr_problem']
        self.q_swpwr_rank = data['swpwr_rank']
        self.q_swpwr_invalid_schemas = data['swpwr_invalid_schemas']
        self.q_swpwr_problem_hints = data['swpwr_problem_hints']

        self.display_name = "Step-by-Step POWER"

        # mcdaniel jul-2020: fix syntax error in print statement
        print(self.display_name)
        return {'result': 'success'}


# SWPWR FINAL RESULTS: Save the final results of the SWPWR React app as a stringified structure.
    @XBlock.json_handler
    def save_swpwr_final_results(self, data, suffix=''):
        if DEBUG: logger.info("SWPWRXBlock save_swpwr_final_results() data={d}".format(d=data))
        self.swpwr_results = json.dumps(data, separators=(',', ':'))
        self.is_answered = True		# We are now done
        if DEBUG: logger.info("SWPWRXBlock save_swpwr_final_results() self.swpwr_results={r}".format(r=self.swpwr_results))
        self.save_grade(data)		# Includes publishing out results to persist them
        if DEBUG: logger.info("SWPWRXBlock save_swpwr_final_results() back from save_grade")
        return {'result': 'success'}

# SWPWR PARTIAL RESULTS: Save the interim results of the SWPWR React app as a stringified structure.
    @XBlock.json_handler
    def save_swpwr_partial_results(self, data, suffix=''):
        if DEBUG: logger.info("SWPWRXBlock save_swpwr_partial_results() data={d}".format(d=data))
        self.swpwr_results = json.dumps(data, separators=(',', ':'))
        self.is_answered = False	# We are not done yet
        if DEBUG: logger.info("SWPWRXBlock save_swpwr_partial_results() self.swpwr_results={r}".format(r=self.swpwr_results))
        self.save_grade(data)		# Includes publishing out results to persist them
        if DEBUG: logger.info("SWPWRXBlock save_swpwr_partial_results() back from save_grade")
        return {'result': 'success'}

    # Do necessary overrides from ScorableXBlockMixin
    def has_submitted_answer(self):
        if DEBUG: logger.info('SWPWRXBlock has_submitted_answer() entered')
        """
        Returns True if the problem has been answered by the runtime user.
        """
        if DEBUG: logger.info("SWPWRXBlock has_submitted_answer() {a}".format(a=self.is_answered))
        return self.is_answered


    def get_score(self):
        if DEBUG: logger.info('SWPWRXBlock get_score() entered')
        """
        Return a raw score already persisted on the XBlock.  Should not
        perform new calculations.
        Returns:
            Score(raw_earned=float, raw_possible=float)
        """
        if DEBUG: logger.info("SWPWRXBlock get_score() earned {e}".format(e=self.raw_earned))
        if DEBUG: logger.info("SWPWRXBlock get_score() max {m}".format(m=self.max_score()))
        return Score(float(self.raw_earned), float(self.max_score()))


    def set_score(self, score):
        """
        Persist a score to the XBlock.
        The score is a named tuple with a raw_earned attribute and a
        raw_possible attribute, reflecting the raw earned score and the maximum
        raw score the student could have earned respectively.
        Arguments:
            score: Score(raw_earned=float, raw_possible=float)
        Returns:
            None
        """
        if DEBUG: logger.info("SWPWRXBlock set_score() earned {e}".format(e=score.raw_earned))
        self.raw_earned = score.raw_earned


    def calculate_score(self):
        """
        Calculate a new raw score based on the state of the problem.
        This method should not modify the state of the XBlock.
        Returns:
            Score(raw_earned=float, raw_possible=float)
        """
        if DEBUG: logger.info("SWPWRXBlock calculate_score() grade {g}".format(g=self.grade))
        if DEBUG: logger.info("SWPWRXBlock calculate_score() max {m}".format(m=self.max_score))
        return Score(float(self.grade), float(self.max_score()))


    def allows_rescore(self):
        """
        Boolean value: Can this problem be rescored?
        Subtypes may wish to override this if they need conditional support for
        rescoring.
        """
        if DEBUG: logger.info("SWPWRXBlock allows_rescore() False")
        return False


    def max_score(self):
        """
        Function which returns the max score for an xBlock which emits a score
        https://openedx.atlassian.net/wiki/spaces/AC/pages/161400730/Open+edX+Runtime+XBlock+API#OpenedXRuntimeXBlockAPI-max_score(self):
        :return: Max Score for this problem
        """
        # Want the normalized, unweighted score here (1), not the points possible (3)
        return 1


    def weighted_grade(self):
        """
        Returns the block's current saved grade multiplied by the block's
        weight- the number of points earned by the learner.
        """
        if DEBUG: logger.info("SWPWRXBlock weighted_grade() earned {e}".format(e=self.raw_earned))
        if DEBUG: logger.info("SWPWRXBlock weighted_grade() weight {w}".format(w=self.q_weight))
        return self.raw_earned * self.q_weight


    def bit_count_ones(self,var):
        """
        Returns the count of one bits in an integer variable
        Note that Python ints are full-fledged objects, unlike in C, so ints are plenty long for these operations.
        """
        if DEBUG: logger.info("SWPWRXBlock bit_count_ones var={v}".format(v=var))
        count=0
        bits = var
        for b in range(32):
            lsb = (bits >> b) & 1;
            count = count + lsb;
        if DEBUG: logger.info("SWPWRXBlock bit_count_ones result={c}".format(c=count))
        return count


    def bit_set_one(self,var,bitnum):
        """
        return var = var with bit 'bitnum' set
        Note that Python ints are full-fledged objects, unlike in C, so ints are plenty long for these operations.
        """
        if DEBUG: logger.info("SWPWRXBlock bit_set_one var={v} bitnum={b}".format(v=var,b=bitnum))
        var = var | (1 << bitnum)
        if DEBUG: logger.info("SWPWRXBlock bit_set_one result={v}".format(v=var))
        return var


    def bit_is_set(self,var,bitnum):
        """
        return True if bit bitnum is set in var
        Note that Python ints are full-fledged objects, unlike in C, so ints are plenty long for these operations.
        """
        if DEBUG: logger.info("SWPWRXBlock bit_is_set var={v} bitnum={b}".format(v=var,b=bitnum))
        result = var & (1 << bitnum)
        if DEBUG: logger.info("SWPWRXBlock bit_is_set result={v} b={b}".format(v=result,b=bool(result)))
        return bool(result)


    def pick_variant(self):
       # pick_variant() selects one of the available question variants that we have not yet attempted.
       # If there is only one variant left, we have to return that one.
       # If there are 2+ variants left, do not return the same one we started with.
       # If we've attempted all variants, we clear the list of attempted variants and pick again.
       #  Returns the question structure for the one we will use this time.

        try:
            prev_index = self.q_index
        except (NameError,AttributeError) as e:
            prev_index = -1

        if DEBUG: logger.info("SWPWRXBlock pick_variant() started replacing prev_index={p}".format(p=prev_index))

        # If there's no self.q_index, then this is our first look at this question in this session, so
        # use self.previous_variant if we can.  This won't restore all previous attempts, but makes sure we
        # don't use the variant that is displayed in the student's last attempt data.
        if (prev_index == -1):
            try:         # use try block in case attribute wasn't saved in previous student work
                 prev_index = self.previous_variant
                 if DEBUG: logger.info("SWPWRXBlock pick_variant() using previous_variant for prev_index={p}".format(p=prev_index))
            except (NameError,AttributeError) as e:
                 if DEBUG: logger.info("SWPWRXBlock pick_variant() self.previous_variant does not exist. Using -1: {e}".format(e=e))
                 prev_index = -1

        if self.bit_count_ones(self.variants_attempted) >= self.variants_count:
            if DEBUG: logger.warn("SWPWRXBlock pick_variant() seen all variants attempted={a} count={c}, clearing variants_attempted".format(a=self.variants_attempted,c=self.variants_count))
            self.variants_attempted = 0			# We have not yet attempted any variants

        tries = 0					# Make sure we dont try forever to find a new variant
        max_tries = 100

        if self.variants_count <= 0:
            if DEBUG: logger.warn("SWPWRXBlock pick_variant() bad variants_count={c}, setting to 1.".format(c=self.variants_count))
            self.variants_count = 1;

        while tries<max_tries:
            tries=tries+1
            q_randint = random.randint(0, ((self.variants_count*100)-1))	# 0..999 for 10 variants, 0..99 for 1 variant, etc.
            if DEBUG: logger.info("SWPWRXBlock pick_variant() try {t}: q_randint={r}".format(t=tries,r=q_randint))
 
            if q_randint>=0 and q_randint<100:
                q_index=0
            elif q_randint>=100 and q_randint<200:
                q_index=1
            elif q_randint>=200 and q_randint<300:
                q_index=2
            elif q_randint>=300 and q_randint<400:
                q_index=3
            elif q_randint>=400 and q_randint<500:
                q_index=4
            elif q_randint>=500 and q_randint<600:
                q_index=5
            elif q_randint>=600 and q_randint<700:
                q_index=6
            elif q_randint>=700 and q_randint<800:
                q_index=7
            elif q_randint>=800 and q_randint<900:
                q_index=8
            else:
                q_index=9

            # If there are 2+ variants left and we have more tries left, do not return the same variant we started with.
            if q_index == prev_index and tries<max_tries and self.bit_count_ones(self.variants_attempted) < self.variants_count-1:
                if DEBUG: logger.info("SWPWRXBlock pick_variant() try {t}: with bit_count_ones(variants_attempted)={v} < variants_count={c}-1 we won't use the same variant {q} as prev variant".format(t=tries,v=self.bit_count_ones(self.variants_attempted),c=self.variants_count,q=q_index))
                break

            if not self.bit_is_set(self.variants_attempted,q_index):
                if DEBUG: logger.info("SWPWRXBlock pick_variant() try {t}: found unattempted variant {q}".format(t=tries,q=q_index))
                break
            else:
                if DEBUG: logger.info("pick_variant() try {t}: variant {q} has already been attempted".format(t=tries,q=q_index))
                if self.bit_count_ones(self.variants_attempted) >= self.variants_count:
                    if DEBUG: logger.info("pick_variant() try {t}: we have attempted all {c} variants. clearning self.variants_attempted.".format(t=tries,c=self.bit_count_ones(self.variants_attempted)))
                    q_index = 0		# Default
                    self.variants_attempted = 0;
                    break

        if tries>=max_tries:
            if DEBUG: logger.error("pick_variant() could not find an unattempted variant of {l} in {m} tries! clearing self.variants_attempted.".format(l=self.q_label,m=max_tries))
            q_index = 0		# Default
            self.variants_attempted = 0;

        if DEBUG: logger.info("pick_variant() Selected variant {v}".format(v=q_index))

        # Note: we won't set self.variants_attempted for this variant until they actually begin work on it (see start_attempt() below)

        question = {
            "q_id" : self.q_id,
            "q_user" : self.xb_user_username,
            "q_index" : 0,
            "q_label" : self.q_label,
            "q_stimulus" : self.q_stimulus,
            "q_definition" : self.q_definition,
            "q_type" :  self.q_type,
            "q_display_math" :  self.q_display_math,
            "q_hint1" :  self.q_hint1,
            "q_hint2" :  self.q_hint2,
            "q_hint3" :  self.q_hint3,
            "q_swpwr_problem" : self.q_swpwr_problem,
            "q_swpwr_rank": self.q_swpwr_rank,
            "q_swpwr_invalid_schemas": self.q_swpwr_invalid_schemas,
            "q_swpwr_problem_hints": self.q_swpwr_problem_hints,
            "q_weight" :  self.my_weight,
            "q_max_attempts" : self.my_max_attempts,
            "q_option_hint" : self.my_option_hint,
            "q_option_showme" : self.my_option_showme,
            "q_grade_showme_ded" : self.my_grade_showme_ded,
            "q_grade_hints_count" : self.my_grade_hints_count,
            "q_grade_hints_ded" : self.my_grade_hints_ded,
            "q_grade_errors_count" : self.my_grade_errors_count,
            "q_grade_errors_ded" : self.my_grade_errors_ded,
            "q_grade_min_steps_count" : self.my_grade_min_steps_count,
            "q_grade_min_steps_ded" : self.my_grade_min_steps_ded,
            "q_grade_app_key" : self.my_grade_app_key
        }

        if DEBUG: logger.info("SWPWRXBlock pick_variant() returned question q_index={i} question={q}".format(i=question['q_index'],q=question))
        return question

