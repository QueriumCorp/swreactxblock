# -*- coding: utf-8 -*-
# pylint: disable=E0401
"""StepWise React xblock

Note that legacy (non-React) stepwise xblock questions can contain up to 10 variants. This xblock code remembers which variants the student has
attempted and if the student requests a new variant, we will try to assign one that has not yet been attempted. Once the
student has attempted all available variants, if they request another variant, we will clear the list of attempted
variants and start assigning variants over again.

FIXME: For the REACT xblock we have currently only implemented one variant per xblock, but some of the variant-related code remains. Caveat Utilitor.

When the student completes work on the StepWise problem (aka 'victory'), we use a callback from the StepWise UI client code
to record the student's score on that attempt.  We also receive a separate callback after the student completes each operation
in the app's phases.

FIXME: It is TBD which event types that we receive these intermediate callbacks for.

We use the CompletableXBlockMixin to support reporting whether student work on an xblock is complete.  The emit_completion
call supports a range from 0.0 (0% complete) to 1.0 (100% complete).  We use only those min and max values.
We could support partial complation, but we don't.  We just want to control whether a green check will appear in the LMS
for this xblock once the student has completed all phases of the StepWise problem.

FIXME: It is TBD whether we want any other phases to mark completion aside from 'Victory'.

When the student completes work on the StepWise problem ('victory'), we use a callback from the StepWise UI client code
to record the student's score on that attempt.

The Javascript code in this xblock displays the score and steps on the student's most recent attempt (only).

Note that the xblock Python code's logic for computing the score is somewhat duplicated in the xblock's Javascript code
since the Javascript is responsible for updating the information displayed to the student on their results, and the
Python code does not currently provide this detailed scoring data down to the Javascript code. It may be possible for
the results of the scoring callback POST to return the scoring details to the Javascript code for display, but this is
not currently done. Thus, if you need to update the scoring logic here in Python, you need to check the Javascript
source in js/src/swreactxstudent.js to make sure you don't also have to change the score display logic there.

To support resuming work on a partially-completed StepWise React problem, we check to see whether there are previous results persisted
in self.swreact_results when we initialize the window.swReact structure to pass to the StepWise React app.  If so, we
unpack that swreact_results attribute and pass oldSession and oldLog back to the React app as two additional attributes in window.swReact.

The swreact_problem_hints field is optional, and looks like this:
swreact.problem.wpHints = [
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
   swreactxstudent.js sets the callback URLs for saving partial results (per step),
   and saving final results (on problem complete).
   For save_swreact_final_results(data), we do:
        (A) set self.swreact_results = json.dumps(data)
        (B) set self.is_answered=True
        (C) call save_grade(data), which should
            (1) set self.solution=data    # We commented out solution for now
            (2) set self.grade=grade
            (3) call self.save() , which does:
                (a) sets the url_name field with a UUID so we have a unique identifier
                (b) calls XBlock.save() to persist our object data
        (D) publish_grade,  which should call
              self.runtime.publish
        (E) call self.emit_completion(1.0) to report that we are complete (1.0)

    save_swreact_partial_results(data) does the same as save_swreact_final_results(),
        except it sets self.is_answered=False and self.emit_completion(0.0)
        also, we want to ignore partial results callbacks if we've previously seen final results.

NOTE: the url_name field in this xblock records a UUID for this xblock instance. This url_name field was added so this
xblock looks like every other standard type of xblock to the OpenEdX runtime (e.g chapter, sequential, vertical, problem).
Having the url_name field in the xblock makes it easier to generate unique xblocks via software, e.g. from StepWise
questions defined in Jira. If a url_name field exists in the xblock, then OpenEdX apparently uses that field value to
uniquely identify the object. Without filling in a value in this field, course imports of XML swreactxblock data will mess
up and all xblocks with a blank value for url_name will be assumed to be the same xblock, which causes the import to
mangle the swreactxblocks in the course import. To ensure that we have a unique value for url_field, the save() routine
checks the url_name field and if it is blank, we generate a UUID to provide a value for that field. Doing the creation of
this field in this manner means that we don't have to expose the url_name field in the studio view and make a question
author invent a unique url_name value for their question.
"""

import json
import random
import uuid
from logging import getLogger

# Python stuff
import pkg_resources

# Open edX stuff
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Boolean, Dict, Float, Integer, Scope, String
from xblock.scorable import ScorableXBlockMixin, Score
from xblock.utils.studio_editable import StudioEditableXBlockMixin
from xblock.completable import CompletableXBlockMixin

# pylint: disable=W0718,C0103
try:
    from lms.djangoapps.courseware.courses import get_course_by_id
except Exception as e:
    description = str(e)
    print(
        f"swreactxblock.swreactxblock.py - lms.djangoapps.courseware.courses import get_course_by_id: {description}"
    )

    def get_course_by_id(course_id: str):
        pass


UNSET = object()

logger = getLogger(__name__)

# DEBUG=settings.ROVER_DEBUG
# DEBUG=False
DEBUG = True
DEFAULT_RANK = "cadet"  # What we'll use for a rank if not modified by the user/default

PASSPREVSESSION = True	# Do pass oldSession and oldLog values

"""The general idea is that we'll determine which question parameters to pass to the StepWise client before invoking it,
making use of course-wide StepWise defaults if set.

If the student has exceeded the max number of attempts (course-wide
setting or per-question setting), we won't let them start another attempt. We'll then get two call-backs:
1. When the student begins work on the question (e.g. submits a first step, clicks 'Hint', or clicks 'Show Solution',
the callback code here will increment the attempts counter.
2. When the student completes the problem ('victory'), we'll compute their grade and save their grade for this attempt.
Note that the student can start an attempt, but never finish (abandoned attempt), but we will still want to count that
attempt.
"""


@XBlock.wants("user")
class SWREACTXBlock(StudioEditableXBlockMixin, ScorableXBlockMixin, CompletableXBlockMixin, XBlock):
    """This xblock provides up to 10 variants of a question for delivery using the StepWise UI."""

    has_author_view = True  # tells the xblock to not ignore the AuthorView
    has_score = True  # tells the xblock to not ignore the grade event
    show_in_read_only_mode = True  # tells the xblock to let the instructor view the student's work (lms/djangoapps/courseware/masquerade.py)

    MAX_VARIANTS = 1  # This code handles 1 variant

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    # Place to store the UUID for this xblock instance.  Not currently displayed in any view.
    url_name = String(display_name="URL name", default="NONE", scope=Scope.content)

    # mcdaniel: added this to work around linter errors
    max_attempts = Integer(
        help="SWREACT Max question attempts", default=3, scope=Scope.content
    )

    # PER-QUESTION GRADING OPTIONS (SEPARATE SET FOR COURSE DEFAULTS)
    q_weight = Float(
        display_name="Problem Weight",
        help="Defines the number of points the problem is worth.",
        scope=Scope.content,
        default=1.0,
        enforce_type=True,
    )

    # NOTE: Don't assume 3 points per problem in swreactxblock
    # q_grade_showme_ded = Float(display_name="Point deduction for using Show Solution",help="SWREACT Raw points deducted from 3.0 (Default: 3.0)", default=3.0, scope=Scope.content)
    q_grade_showme_ded = Float(
        display_name="Point deduction for using Show Solution",
        help="SWREACT Raw points deducted from 1.0 (Default: 0.25)",
        default=0.25,
        scope=Scope.content,
    )
    q_grade_hints_count = Integer(
        help="SWREACT Number of Hints before deduction",
        default=2,
        scope=Scope.content,
    )
    q_grade_hints_ded = Float(
        help="SWREACT Point deduction for using excessive Hints",
        default=1.0,
        scope=Scope.content,
    )
    q_grade_errors_count = Integer(
        help="SWREACT Number of Errors before deduction",
        default=2,
        scope=Scope.content,
    )
    q_grade_errors_ded = Float(
        help="SWREACT Point deduction for excessive Errors",
        default=1.0,
        scope=Scope.content,
    )
    q_grade_min_steps_count = Integer(
        help="SWREACT Minimum valid steps in solution for full credit",
        default=3,
        scope=Scope.content,
    )
    q_grade_min_steps_ded = Float(
        help="SWREACT Point deduction for fewer than minimum valid steps",
        default=0.25,
        scope=Scope.content,
    )
    # NOTE: Don't assume 3 points per problem in swreactxblock, so don't deduct 0.25 in swreactxblock for min steps
    # q_grade_min_steps_ded = Float(help="SWREACT Point deduction for fewer than minimum valid steps", default=0.25, scope=Scope.content)
    q_grade_app_key = String(
        help="SWREACT question app key", default="SBIRPhase2", scope=Scope.content
    )

    # PER-QUESTION HINTS/SHOW SOLUTION OPTIONS
    q_option_hint = Boolean(
        help='SWREACT Display Hint button if "True"',
        default=True,
        scope=Scope.content,
    )
    q_option_showme = Boolean(
        help='SWREACT Display ShowSolution button if "True"',
        default=True,
        scope=Scope.content,
    )

    # MAX ATTEMPTS PER-QUESTION OVERRIDE OF COURSE DEFAULT
    q_max_attempts = Integer(
        help="SWREACT Max question attempts (-1 = Use Course Default)",
        default=-1,
        scope=Scope.content,
    )

    # STEP-WISE QUESTION DEFINITION FIELDS FOR VARIANTS
    display_name = String(
        display_name="SWREACT Display name", default="SWREACT", scope=Scope.content
    )

    q_id = String(help="Question ID", default="", scope=Scope.content)
    q_label = String(help="SWREACT Question label", default="", scope=Scope.content)
    q_stimulus = String(
        help="SWREACT Stimulus",
        default="Solve for \\(a\\). \\(5a+4=2a-5\\)",
        scope=Scope.content,
    )
    q_definition = String(
        help="SWREACT Definition",
        default="SolveFor[5a+4=2a-5,a]",
        scope=Scope.content,
    )
    q_type = String(help="SWREACT Type", default="gradeBasicAlgebra", scope=Scope.content)
    q_display_math = String(
        help="SWREACT Display Math", default="\\(\\)", scope=Scope.content
    )
    q_hint1 = String(help="SWREACT First Math Hint", default="", scope=Scope.content)
    q_hint2 = String(help="SWREACT Second Math Hint", default="", scope=Scope.content)
    q_hint3 = String(help="SWREACT Third Math Hint", default="", scope=Scope.content)
    q_swreact_problem = String(
        help="SWREACT SWREACT Problem", default="", scope=Scope.content
    )
    # Invalid schema choices should be a CSV list of one or more of these: "TOTAL", "DIFFERENCE", "CHANGEINCREASE", "CHANGEDECREASE", "EQUALGROUPS", and "COMPARE"
    # Invalid schema choices can also be the official names: "additiveTotalSchema", "additiveDifferenceSchema", "additiveChangeSchema", "subtractiveChangeSchema", "multiplicativeEqualGroupsSchema", and "multiplicativeCompareSchema"
    # This Xblock converts the upper-case names to the official names when constructing the launch code for the React app, so you can mix these names.
    # Note that this code doesn't validate these schema names, so Caveat Utilitor.
    q_swreact_invalid_schemas = String(
        display_name="Comma-separated list of unallowed schema names",
        help="SWREACT Comma-seprated list of unallowed schema names",
        default="",
        scope=Scope.content,
    )
    # Rank choices should be "newb" or "cadet" or "learner" or "ranger"
    q_swreact_rank = String(
        display_name="Student rank for this question",
        help="SWREACT Student rank for this question",
        default=DEFAULT_RANK,
        scope=Scope.content,
    )
    q_swreact_problem_hints = String(
        display_name="Problem-specific hints (JSON)",
        help="SWREACT optional problem-specific hints (JSON)",
        default="[]",
        scope=Scope.content,
    )
    # STUDENT'S QUESTION PERFORMANCE FIELDS
    swreact_results = String(
        help="SWREACT The student's SWREACT Solution structure",
        default="",
        scope=Scope.user_state,
    )

    xb_user_username = String(
        help="SWREACT The user's username", default="", scope=Scope.user_state
    )
    xb_user_fullname = String(
        help="SWREACT The user's fullname", default="", scope=Scope.user_state
    )
    grade = Float(help="SWREACT The student's grade", default=-1, scope=Scope.user_state)
    # solution = Dict(help="SWREACT The student's last stepwise solution", default={}, scope=Scope.user_state)
    question = Dict(
        help="SWREACT The student's current stepwise question",
        default={},
        scope=Scope.user_state,
    )
    # count_attempts keeps track of the number of attempts of this question by this student so we can
    # compare to course.max_attempts which is inherited as an per-question setting or a course-wide setting.
    count_attempts = Integer(
        help="SWREACT Counted number of questions attempts",
        default=0,
        scope=Scope.user_state,
    )
    raw_possible = Float(
        help="SWREACT Number of possible points", default=1, scope=Scope.user_state
    )
    # NOTE: Don't assume 3 points per problem in swreactxblock
    # raw_possible = Float(help="SWREACT Number of possible points", default=3,scope=Scope.user_state)
    # The following 'weight' is examined by the standard scoring code, so needs to be set once we determine which weight value to use
    # (per-Q or per-course). Also used in rescoring by override_score_module_state.
    weight = Float(
        help="SWREACT Defines the number of points the problem is worth.",
        default=1,
        scope=Scope.user_state,
    )

    my_weight = Integer(
        help="SWREACT Remember weight course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_max_attempts = Integer(
        help="SWREACT Remember max_attempts course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_option_showme = Integer(
        help="SWREACT Remember option_showme course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_option_hint = Integer(
        help="SWREACT Remember option_hint course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_grade_showme_ded = Integer(
        help="SWREACT Remember grade_showme_ded course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_grade_hints_count = Integer(
        help="SWREACT Remember grade_hints_count course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_grade_hints_ded = Integer(
        help="SWREACT Remember grade_hints_ded course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_grade_errors_count = Integer(
        help="SWREACT Remember grade_errors_count course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_grade_errors_ded = Integer(
        help="SWREACT Remember grade_errors_ded course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_grade_min_steps_count = Integer(
        help="SWREACT Remember grade_min_steps_count course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_grade_min_steps_ded = Integer(
        help="SWREACT Remember grade_min_steps_ded course setting vs question setting",
        default=-1,
        scope=Scope.user_state,
    )
    my_grade_app_key = String(
        help="SWREACT Remember app_key course setting vs question setting",
        default="SBIRPhase2",
        scope=Scope.user_state,
    )

    # variant_attempted: Remembers the set of variant q_index values the student has already attempted.
    # We can't add a Set to Scope.user_state, or we get get runtime errors whenever we update this field:
    #      variants_attempted = Set(scope=Scope.user_state)
    #      TypeError: Object of type set is not JSON serializable
    # See e.g. this:  https://stackoverflow.com/questions/8230315/how-to-json-serialize-sets
    # So we'll leave the variants in an Integer field and fiddle the bits ourselves :-(
    # We define our own bitwise utility functions below: bit_count_ones() bit_is_set() bit_is_set()

    variants_attempted = Integer(
        help="SWREACT Bitmap of attempted variants", default=0, scope=Scope.user_state
    )
    variants_count = Integer(
        help="SWREACT Count of available variants", default=0, scope=Scope.user_state
    )
    previous_variant = Integer(
        help="SWREACT Index (q_index) of the last variant used",
        default=-1,
        scope=Scope.user_state,
    )

    # FIELDS FOR THE ScorableXBlockMixin

    is_answered = Boolean(
        default=False,
        scope=Scope.user_state,
        help='Will be set to "True" if successfully answered',
    )

    correct = Boolean(
        default=False,
        scope=Scope.user_state,
        help='Will be set to "True" if correctly answered',
    )

    raw_earned = Float(
        help="SWREACT Keeps maximum score achieved by student as a raw value between 0 and 1.",
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
        """The STUDENT view of the SWREACTXBlock, shown to students when viewing courses.

        We set up the question parameters (referring to course-wide settings), then launch the javascript StepWise
        client.
        """
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() entered. context={context}".format(
                    context=context
                )
            )

        if DEBUG:
            logger.info("SWREACTXBlock student_view() self={a}".format(a=self))
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.runtime={a}".format(a=self.runtime)
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.runtime.course_id={a}".format(
                    a=self.runtime.course_id
                )
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.variants_attempted={v}".format(
                    v=self.variants_attempted
                )
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.previous_variant={v}".format(
                    v=self.previous_variant
                )
            )

        course = get_course_by_id(self.runtime.course_id)
        if DEBUG:
            logger.info("SWREACTXBlock student_view() course={c}".format(c=course))

        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() max_attempts={a} q_max_attempts={b}".format(
                    a=self.max_attempts, b=self.q_max_attempts
                )
            )

        # NOTE: Can't set a self.q_* field here if an older imported swreactxblock doesn't define this field, since it defaults to None
        # (read only?) so we'll use instance vars my_* to remember whether to use the course-wide setting or the per-question setting.
        # Similarly, some old courses may not define the stepwise advanced
        # settings we want, so we create local variables for them.

        # For per-xblock settings
        temp_weight = -1
        temp_max_attempts = -1
        temp_option_hint = -1
        temp_option_showme = -1
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
        def_course_stepwise_option_hint = True
        def_course_stepwise_option_showme = True
        def_course_stepwise_grade_showme_ded = 0.25
        # NOTE: Don't assume 3 points per problem in swreactxblock
        # def_course_stepwise_grade_showme_ded = 3.0
        def_course_stepwise_grade_hints_count = 2
        def_course_stepwise_grade_hints_ded = 1.0
        def_course_stepwise_grade_errors_count = 2
        def_course_stepwise_grade_errors_ded = 1.0
        def_course_stepwise_grade_min_steps_count = 3
        def_course_stepwise_grade_min_steps_ded = 0.0
        # NOTE: Don't assume a min steps deduction in swreactxblock
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
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_weight was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_weight = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_weight: {t}".format(t=temp_weight)
            )

        try:
            temp_max_attempts = self.q_max_attempts
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_max_attempts was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_max_attempts = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_max_attempts: {t}".format(
                    t=temp_max_attempts
                )
            )

        try:
            temp_option_hint = self.q_option_hint
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.option_hint was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_option_hint = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_option_hint: {t}".format(
                    t=temp_option_hint
                )
            )

        try:
            temp_option_showme = self.q_option_showme
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.option_showme was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_option_showme = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_option_showme: {t}".format(
                    t=temp_option_showme
                )
            )

        try:
            temp_grade_showme_ded = self.q_grade_showme_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_grade_showme_ded was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_grade_showme_ded = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_grade_showme_ded: {t}".format(
                    t=temp_grade_showme_ded
                )
            )

        try:
            temp_grade_hints_count = self.q_grade_hints_count
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_grade_hints_count was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_grade_hints_count = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_grade_hints_count: {t}".format(
                    t=temp_grade_hints_count
                )
            )

        try:
            temp_grade_hints_ded = self.q_grade_hints_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_grade_hints_ded was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_grade_hints_ded = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_grade_hints_ded: {t}".format(
                    t=temp_grade_hints_ded
                )
            )

        try:
            temp_grade_errors_count = self.q_grade_errors_count
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_grade_errors_count was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_grade_errors_count = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_grade_errors_count: {t}".format(
                    t=temp_grade_errors_count
                )
            )

        try:
            temp_grade_errors_ded = self.q_grade_errors_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_grade_errors_ded was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_grade_errors_ded = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_grade_errors_ded: {t}".format(
                    t=temp_grade_errors_ded
                )
            )

        try:
            temp_grade_min_steps_count = self.q_grade_min_steps_count
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_grade_min_steps_count was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_grade_min_steps_count = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_grade_min_steps_count: {t}".format(
                    t=temp_grade_min_steps_count
                )
            )

        try:
            temp_grade_min_steps_ded = self.q_grade_min_steps_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_grade_min_steps_ded was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_grade_min_steps_ded = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_grade_min_steps_ded: {t}".format(
                    t=temp_grade_min_steps_ded
                )
            )

        try:
            temp_grade_app_key = self.q_grade_app_key
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_grade_app_key was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_grade_app_key = ""
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_grade_app_key: {t}".format(
                    t=temp_grade_app_key
                )
            )

        # Fetch the course-wide settings if they exist, otherwise create a default

        try:
            temp_course_stepwise_weight = course.stepwise_weight
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_weight was not defined in this instance: {e}".format(
                        e=e
                    )
                )
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_weight: {s}".format(
                    s=temp_course_stepwise_weight
                )
            )

        try:
            temp_course_stepwise_max_attempts = course.stepwise_max_attempts
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_max_attempts was not defined in this instance: {e}".format(
                        e=e
                    )
                )
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_max_attempts: {s}".format(
                    s=temp_course_stepwise_max_attempts
                )
            )

        try:
            temp_course_stepwise_option_showme = course.stepwise_option_showme
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_option_showme was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_option_showme = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_option_showme: {s}".format(
                    s=temp_course_stepwise_option_showme
                )
            )

        try:
            temp_course_stepwise_option_hint = course.stepwise_option_hint
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_option_hint was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_option_hint = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_option_hint: {s}".format(
                    s=temp_course_stepwise_option_hint
                )
            )

        try:
            temp_course_stepwise_grade_hints_count = course.stepwise_grade_hints_count
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_settings_grade_hints_count was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_grade_hints_count = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_grade_hints_count: {s}".format(
                    s=temp_course_stepwise_grade_hints_count
                )
            )

        try:
            temp_course_stepwise_grade_showme_ded = course.stepwise_grade_showme_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_grade_showme_ded was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_grade_showme_ded = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_grade_showme_ded: {s}".format(
                    s=temp_course_stepwise_grade_showme_ded
                )
            )

        try:
            temp_course_stepwise_grade_hints_ded = course.stepwise_grade_hints_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_grade_hints_ded was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_grade_hints_ded = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_grade_hints_ded: {s}".format(
                    s=temp_course_stepwise_grade_hints_ded
                )
            )

        try:
            temp_course_stepwise_grade_errors_count = course.stepwise_grade_errors_count
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_grade_errors_count was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_grade_errors_count = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_grade_errors_count: {s}".format(
                    s=temp_course_stepwise_grade_errors_count
                )
            )

        try:
            temp_course_stepwise_grade_errors_ded = course.stepwise_grade_errors_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_grade_errors_ded was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_grade_errors_ded = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_grade_errors_ded: {s}".format(
                    s=temp_course_stepwise_grade_errors_ded
                )
            )

        try:
            temp_course_stepwise_grade_min_steps_count = (
                course.stepwise_grade_min_steps_count
            )
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_grade_min_steps_count was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_grade_min_steps_count = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_grade_min_steps_count: {s}".format(
                    s=temp_course_stepwise_grade_min_steps_count
                )
            )

        try:
            temp_course_stepwise_grade_min_steps_ded = (
                course.stepwise_grade_min_steps_ded
            )
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_grade_min_steps_ded was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_grade_min_steps_ded = -1
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_grade_min_steps_ded: {s}".format(
                    s=temp_course_stepwise_grade_min_steps_ded
                )
            )

        try:
            temp_course_stepwise_app_key = course.stepwise_grade_app_key
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() course.stepwise_grade_app_key was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            temp_course_stepwise_grade_app_key = ""
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() temp_course_stepwise_grade_app_key: {s}".format(
                    s=temp_course_stepwise_grade_app_key
                )
            )

        # Enforce course-wide grading options here.
        # We prefer the per-question setting to the course setting.
        # If neither the question setting nor the course setting exist, use the course default.

        if temp_weight != -1:
            self.my_weight = temp_weight
        elif temp_course_stepwise_weight != -1:
            self.my_weight = temp_course_stepwise_weight
        else:
            self.my_weight = def_course_stepwise_weight
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_weight={m}".format(m=self.my_weight)
            )

        # Set the real object weight here how that we know all of the weight settings (per-Q vs. per-course).
        # weight is used by the real grading code e.g. for overriding student scores.
        self.weight = self.my_weight
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.weight={m}".format(m=self.weight)
            )

        # For max_attempts: If there is a per-question max_attempts setting, use that.
        # Otherwise, if there is a course-wide stepwise_max_attempts setting, use that.
        # Otherwise, use the course-wide max_attempts setting that is used for CAPA (non-StepWise) problems.

        if temp_max_attempts is None:
            temp_max_attempts = -1

        if temp_max_attempts != -1:
            self.my_max_attempts = temp_max_attempts
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() my_max_attempts={a} temp_max_attempts={m}".format(
                        a=self.my_max_attempts, m=temp_max_attempts
                    )
                )
        elif temp_course_stepwise_max_attempts != -1:
            self.my_max_attempts = temp_course_stepwise_max_attempts
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() my_max_attempts={a} temp_course_stepwise_max_attempts={m}".format(
                        a=self.my_max_attempts, m=temp_course_stepwise_max_attempts
                    )
                )
        else:
            self.my_max_attempts = course.max_attempts
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() my_max_attempts={a} course.max_attempts={m}".format(
                        a=self.my_max_attempts, m=course.max_attempts
                    )
                )

        if temp_option_hint != -1:
            self.my_option_hint = temp_option_hint
        elif temp_course_stepwise_option_hint != -1:
            self.my_option_hint = temp_course_stepwise_option_hint
        else:
            self.my_option_hint = def_course_stepwise_option_hint
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_option_hint={m}".format(
                    m=self.my_option_hint
                )
            )

        if temp_option_showme != -1:
            self.my_option_showme = temp_option_showme
        elif temp_course_stepwise_option_showme != -1:
            self.my_option_showme = temp_course_stepwise_option_showme
        else:
            self.my_option_showme = def_course_stepwise_option_showme
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_option_showme={m}".format(
                    m=self.my_option_showme
                )
            )

        if temp_grade_showme_ded != -1:
            self.my_grade_showme_ded = temp_grade_showme_ded
        elif temp_course_stepwise_grade_showme_ded != -1:
            self.my_grade_showme_ded = temp_course_stepwise_grade_showme_ded
        else:
            self.my_grade_showme_ded = def_course_stepwise_grade_showme_ded
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_grade_showme_ded={m}".format(
                    m=self.my_grade_showme_ded
                )
            )

        if temp_grade_hints_count != -1:
            self.my_grade_hints_count = temp_grade_hints_count
        elif temp_course_stepwise_grade_hints_count != -1:
            self.my_grade_hints_count = temp_course_stepwise_grade_hints_count
        else:
            self.my_grade_hints_count = def_course_stepwise_grade_hints_count
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_grade_hints_count={m}".format(
                    m=self.my_grade_hints_count
                )
            )

        if temp_grade_hints_ded != -1:
            self.my_grade_hints_ded = temp_grade_hints_ded
        elif temp_course_stepwise_grade_hints_ded != -1:
            self.my_grade_hints_ded = temp_course_stepwise_grade_hints_ded
        else:
            self.my_grade_hints_ded = def_course_stepwise_grade_hints_ded
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_grade_hints_ded={m}".format(
                    m=self.my_grade_hints_ded
                )
            )

        if temp_grade_errors_count != -1:
            self.my_grade_errors_count = temp_grade_errors_count
        elif temp_course_stepwise_grade_errors_count != -1:
            self.my_grade_errors_count = temp_course_stepwise_grade_errors_count
        else:
            self.my_grade_errors_count = def_course_stepwise_grade_errors_count
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_grade_errors_count={m}".format(
                    m=self.my_grade_errors_count
                )
            )

        if temp_grade_errors_ded != -1:
            self.my_grade_errors_ded = temp_grade_errors_ded
        elif temp_course_stepwise_grade_errors_ded != -1:
            self.my_grade_errors_ded = temp_course_stepwise_grade_errors_ded
        else:
            self.my_grade_errors_ded = def_course_stepwise_grade_errors_ded
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_grade_errors_ded={m}".format(
                    m=self.my_grade_errors_ded
                )
            )

        if temp_grade_min_steps_count != -1:
            self.my_grade_min_steps_count = temp_grade_min_steps_count
        elif temp_course_stepwise_grade_min_steps_count != -1:
            self.my_grade_min_steps_count = temp_course_stepwise_grade_min_steps_count
        else:
            self.my_grade_min_steps_count = def_course_stepwise_grade_min_steps_count
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_grade_min_steps_count={m}".format(
                    m=self.my_grade_min_steps_count
                )
            )

        if temp_grade_min_steps_ded != -1:
            self.my_grade_min_steps_ded = temp_grade_min_steps_ded
        elif temp_course_stepwise_grade_min_steps_ded != -1:
            self.my_grade_min_steps_ded = temp_course_stepwise_grade_min_steps_ded
        else:
            self.my_grade_min_steps_ded = def_course_stepwise_grade_min_steps_ded
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_grade_min_steps_ded={m}".format(
                    m=self.my_grade_min_steps_ded
                )
            )

        if temp_grade_app_key != "":
            self.my_grade_app_key = temp_grade_app_key
        elif temp_course_stepwise_grade_app_key != "":
            self.my_grade_app_key = temp_course_stepwise_grade_app_key
        else:
            self.my_grade_app_key = def_course_stepwise_grade_app_key

        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.my_grade_app_key={m}".format(
                    m=self.my_grade_app_key
                )
            )

        # Fetch the new xblock-specific attributes if they exist, otherwise set them to a default
        try:
            temp_value = self.q_swreact_invalid_schemas
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_swreact_invalid_schemas was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            self.q_swreact_invalid_schemas = ""
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.q_swreact_invalid_schemas: {t}".format(
                    t=self.q_swreact_invalid_schemas
                )
            )
        try:
            temp_value = self.q_swreact_rank
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_swreact_rank was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            self.q_swreact_rank = DEFAULT_RANK
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.q_swreact_rank: {t}".format(
                    t=self.q_swreact_rank
                )
            )
        try:
            temp_value = self.q_swreact_problem_hints
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() self.q_swreact_problem_hints was not defined in this instance: {e}".format(
                        e=e
                    )
                )
            self.q_swreact_problem_hints = "[]"
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.q_swreact_problem_hints: {t}".format(
                    t=self.q_swreact_problem_hints
                )
            )

        # Save an identifier for the user and their full name

        user_service = self.runtime.service(self, "user")
        xb_user = user_service.get_current_user()
        self.xb_user_username = user_service.get_current_user().opt_attrs.get(
            "edx-platform.username"
        )
        if self.xb_user_username is None:
            if DEBUG:
                logger.error("SWREACTXBlock self.xb_user_username was None")
            self.xb_user_username = "FIXME"
        if self.xb_user_username == "":
            if DEBUG:
                logger.error("SWREACTXBlock self.xb_user_username was empty")
            self.xb_user_username = "FIXME"
        self.xb_user_fullname = xb_user.full_name
        if self.xb_user_fullname is None:
            if DEBUG:
                logger.error("SWREACTXBlock self.xb_user_fullname was None")
            self.xb_user_fullname = "FIXME FIXME"
        if self.xb_user_fullname == "":
            if DEBUG:
                logger.error("SWREACTXBlock self.xb_user_fullname was empty")
            self.xb_user_fullname = "FIXME FIXME"
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.xb_user_username: {e} self.xb_user_fullname: {f}".format(
                    e=self.xb_user_username, f=self.xb_user_fullname
                )
            )

        # Determine which stepwise variant to use

        self.variants_count = 1

        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() self.variants_count={c}".format(
                    c=self.variants_count
                )
            )
        # Pick a variant at random, and make sure that it is one we haven't attempted before.

        random.seed()  # Use the clock to seed the random number generator for picking variants
        self.question = self.pick_variant()

        # question = self.question		# Don't need local var
        q_index = self.question["q_index"]

        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() pick_variant selected q_index={i} question={q}".format(
                    i=q_index, q=self.question
                )
            )

        # NOTE: The following page now includes the script tag that loads the module for the main React app
        html = self.resource_string("static/html/swreactxstudent.html")
        frag = Fragment(html.format(self=self))

        frag.add_resource('<meta charset="UTF-8"/>', "text/html", "head")
        frag.add_resource(
            '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />',
            "text/html",
            "head",
        )
        frag.add_resource(
            '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />',
            "text/html",
            "head",
        )
        frag.add_resource(
            '<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />',
            "text/html",
            "head",
        )
        frag.add_resource(
            '<meta name="viewport" content="width=device-width,initial-scale=1.0"/>',
            "text/html",
            "head",
        )
        frag.add_resource(
            '<link rel="preconnect" href="https://fonts.googleapis.com" />',
            "text/html",
            "head",
        )
        frag.add_resource(
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />',
            "text/html",
            "head",
        )
        frag.add_resource(
            '<link href="https://fonts.googleapis.com/css2?family=Capriola&family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&family=Irish+Grover&display=swap" rel="stylesheet" />',
            "text/html",
            "head",
        )
        frag.add_resource("<title>Querium StepWise React</title>", "text/html", "head")

        frag.add_css(self.resource_string("static/css/swreactxstudent.css"))
        frag.add_javascript(self.resource_string("static/js/src/swreactxstudent.js"))

        # Now we can finally add the React app bundle assets
        frag.add_javascript(
            self.resource_string("static/js/src/final_callback.js")
        )  # Final submit callback code and define swreact_problems[]

        # Add our own snippet of javascript code so we can add debugging code on
        # the fly without re-building the xblock
        frag.add_javascript_url(
            "//swm-openedx-us-dev-storage.s3.us-east-2.amazonaws.com/static/js/swreactxblock.js"
        )
        # Add bugfender library for console log capture
        frag.add_javascript_url("//js.bugfender.com/bugfender-v2.js")
        frag.add_resource(
            "<script type=\"module\"> Bugfender.init({ appKey: 'rLBi6ZTSwDd3FEM8EhHlrlQRXpiHvZkt', apiURL: 'https://api.bugfender.com/', baseURL: 'https://dashboard.bugfender.com/', version: '1.9.203'}); Bugfender.setDeviceKey('username', '"
            + self.xb_user_username
            + "'); </script>",
            "text/html",
            "head",
        )
        # Invalid schema choices should be a CSV list of one or more of these: "TOTAL", "DIFFERENCE", "CHANGEINCREASE", "CHANGEDECREASE", "EQUALGROUPS", and "COMPARE"
        # Invalid schema choices can also be the official names: "additiveTotalSchema", "additiveDifferenceSchema", "additiveChangeSchema", "subtractiveChangeSchema", "multiplicativeEqualGroupsSchema", and "multiplicativeCompareSchema"
        # Convert the upper-case names to the 'official' names. NB: The order of
        # .replace() calls might matter if one of these schema names is a
        # substring of another name.
        invalid_schemas_js = self.q_swreact_invalid_schemas
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() before mapping loop invalid_schemas_js={e}".format(
                    e=invalid_schemas_js
                )
            )
        mapping = {
            "TOTAL": "additiveTotalSchema",
            "DIFFERENCE": "additiveDifferenceSchema",
            "CHANGEINCREASE": "additiveChangeSchema",
            "CHANGEDECREASE": "subtractiveChangeSchema",
            "EQUALGROUPS": "multiplicativeEqualGroupsSchema",
            "COMPARE": "multiplicativeCompareSchema",
        }
        for schema_key, schema_value in mapping.items():
            invalid_schemas_js = invalid_schemas_js.replace(
                schema_key, schema_value
            )
            if DEBUG:
                logger.info(
                    "SWREACTXBlock student_view() in mapping loop schema_key={k} schema_value={v} invalid_schemas_js={e}".format(
                        k=schema_key, v=schema_value, e=invalid_schemas_js
                    )
                )

        # We use the window.swreact DOM element to communicate the  problem definition to the React app.
        # We construct that Javascript structure here.

        # FIXME: What is the name of the top-level DOM element we are looking for, e.g. is it swReact?

        swreact_string = (
            "window.swReact = {"
            )
        # If we have persisted previous results in self.swreact_results, pass those results back to the swReact React app
        # in the 'oldSession' and 'oldLog' attributes.
        try:
           swreact_results = self.swreact_results
        except (NameError, AttributeError) as e:
           if DEBUG:
              logger.info(
                 "SWREACTXBlock save_grade() self.swreact_results was not defined when building swreact_string: {e}".format(e=e)
              )
              swreact_results = ""

        if (PASSPREVSESSION and (len(swreact_results) > 0)):
            # Parse any existing JSON results string to a 2-element Python list of [session and log[]]
            try:
               json_array = json.loads(swreact_results)
            except Exception as e:
               logger.error(
                  "SWREACTXBlock student_view() in setting swreact_string could not load json from swreact_results: {e}".format(e=e)
               )
            else:
               session_element = json_array[0]
               log_element =     json_array[1]

               # Convert the first element back to a JSON string
               session_element_string = json.dumps(session_element)

               # Convert the second element back to a JSON string
               log_element_string = json.dumps(log_element)

               if DEBUG:
                   logger.info(
                       "SWREACTXBlock student_view() in setting swreact_string session_element_str={s}".format(
                           s=session_element_string
                       )
                   )
                   logger.info(
                       "SWREACTXBlock student_view() in setting swreact_string log_element_str={l}".format(
                           l=log_element_string
                       )
                   )
               swreact_string = ( swreact_string
                   + '    oldSession: "'
                   + session_element_string.replace('"', "&quot;")
                   + '",'
                   + '    oldLog: "'
                   + log_element_string.replace('"', "&quot;")
                   + '",'
                   + '    oldSessionLogCombo: "'
                   + swreact_results.replace('"', "&quot;")
                   + '",'
                   )
        else:
            # If no previous attempt data, set these to empty values
            swreact_string = ( swreact_string
                + '    oldSession: "{}",'
                + '    oldLog: "[]",'
                )

        # Once we have dealt with adding oldSession and oldLog to swreact_string if necessary, we set the rest of the problem attributes:
        # 'options', 'student', 'problem', and 'handlers'
        # The 'handlers' attribute are for our callbacks: onComplete and onStep.

        swreact_string = ( swreact_string
            + "    options: {"
            + '        swapiUrl: "https://swapi2.onrender.com", '
            + '        gltfUrl: "https://s3.amazonaws.com/stepwise-editorial.querium.com/swReact/dist/models/", '
            + '        rank: "'
            + self.q_swreact_rank
            + '", '
            + '        disabledSchemas: "'
            + invalid_schemas_js
            + '"'
            + "    }, "
            + "    student: { "
            + '        studentId: "'
            + self.xb_user_username
            + '", '
            + '        fullName: "'
            + self.xb_user_fullname
            + '", '
            + '        familiarName: "'
            + "NONE"
            + '"'
            + "    },"
            + "    problem: { "
            + '        appKey: "'
            + self.q_grade_app_key
            + '", '
            + '        policyId: "'
            + "$A9$"
            + '", '
            + '        problemId: "'
            + self.q_id
            + '", '
            + '        title: "'
            + "SAMPLE"
            + '", '
            + "        stimulus: '"
            + str(self.q_stimulus).replace("'", "&apos;")
            + "', "
            + '        topic: "'
            + "gradeBasicAlgebra"
            + '", '
            + "        definition: '"
            + str(self.q_definition).replace("'", "&apos;")
            + "', "
            + "        wpHintsString: '"
            + str(self.q_swreact_problem_hints).replace("'", "&apos;")
            + "', "
            + "        mathHints: ["
            + '                   "'
            + str(self.q_hint1).replace("'", "&apos;").replace('"', "&quot;")
            + '",'
            + '                   "'
            + str(self.q_hint2).replace("'", "&apos;").replace('"', "&quot;")
            + '",'
            + '                   "'
            + str(self.q_hint3).replace("'", "&apos;").replace('"', "&quot;")
            + '"'
            + "                   ]"
            + "    },"
            + "    handlers: {"
            + "        onComplete: (session,log) => {"
            + '            console.info("onComplete session",session);'
            + '            console.info("onComplete log",log);'
            + '            console.info("onComplete handlerUrlSwreactFinalResults",handlerUrlSwreactFinalResults);'
            + "            const solution = [session,log];"
            + "            var solution_string = JSON.stringify(solution);"
            + '            console.info("onComplete solution_string",solution_string);'
            + "            $.ajax({"
            + '                type: "POST",'
            + "                url: handlerUrlSwreactFinalResults,"
            + "                data: solution_string,"
            + "                success: function (data,msg) {"
            + '                    console.info("onComplete solution POST success");'
            + '                    console.info("onComplete solution POST data",data);'
            + '                    console.info("onComplete solution POST msg",msg);'
            + "                },"
            + "                error: function(XMLHttpRequest, textStatus, errorThrown) {"
            + '                    console.info("onComplete solution POST error textStatus=",textStatus," errorThrown=",errorThrown);'
            + "                }"
            + "            });"
            + "            $('.problem-complete').show();"
            + "            $('.unit-navigation').show();"
            + "        },"
            + "        onStep: (session,log) => {"
            + '            console.info("onStep session",session);'
            + '            console.info("onStep log",log);'
            + '            console.info("onStep handlerUrlSwreactPartialResults",handlerUrlSwreactPartialResults);'
            + "            const solution = [session,log];"
            + "            var solution_string = JSON.stringify(solution);"
            + '            console.info("onStep solution_string",solution_string);'
            + "            $.ajax({"
            + '                type: "POST",'
            + "                url: handlerUrlSwreactPartialResults,"
            + "                data: solution_string,"
            + "                success: function (data,msg) {"
            + '                    console.info("onStep solution POST success");'
            + '                    console.info("onStep solution POST data",data);'
            + '                    console.info("onStep solution POST msg",msg);'
            + "                },"
            + "                error: function(XMLHttpRequest, textStatus, errorThrown) {"
            + '                    console.info("onStep solution POST error textStatus=",textStatus," errorThrown=",errorThrown);'
            + "                }"
            + "            });"
            + "        }"
            + "    }"
            + "};"
            + "try { "
            + '    console.log( "before JSON.parse wpHintsString ",window.swReact.problem.wpHintsString);'
            + "    window.swReact.problem.wpHints = JSON.parse(window.swReact.problem.wpHintsString);"
            + '    console.log( "wpHints data is ",window.swReact.problem.wpHints );'
            + "} catch(e) {"
            + '    console.log( "Could not decode wpHints string",e.message );'
            + "};"
        )
        if DEBUG:
            logger.info(
                "SWREACTXBlock student_view() swreact_string={e}".format(e=swreact_string)
            )
        frag.add_resource(swreact_string, "application/javascript", "foot")

        frag.initialize_js("SWREACTXStudent", {})  # Call the entry point
        return frag

    def publish_grade(self):
        """Publish the grade for this block, for rescoring events."""
        if DEBUG:
            logger.info(
                "SWREACTXBlock publish_grade() pretrimmed self.raw_earned={e} self.weight={w}".format(
                    e=self.raw_earned, w=self.weight
                )
            )
        self.raw_earned = max(self.raw_earned, 0.0)
        self.raw_earned = min(self.raw_earned, self.weight)
        if DEBUG:
            logger.info(
                "SWREACTXBlock publish_grade() posttrimmed self.raw_earned={e} self.weight={w}".format(
                    e=self.raw_earned, w=self.weight
                )
            )
        self.runtime.publish(
            self,
            "grade",
            {"value": self.raw_earned * 1.0, "max_value": self.weight * 1.0},
        )

    def save(self):
        """Save this block to the database."""
        if DEBUG:
            logger.info("SWREACTXBlock save() self{s}".format(s=self))
        # If we don't have a url_name for this xblock defined to make the xblock unique, assign ourselves a unique UUID4 as a hex string.
        # Otherwise course imports can confuse multiple swreactxblocks with url_name == "NONE" (the default)
        # We don't currently allow authors to specify a value for this field in studio since we don't want to burden them with assigning UUIDs.
        # There was also a long period of time prior to September 2024 where we didn't assign any value to this field, so we try to catch
        # such swreactxblocks and correct this at the time of the next save()
        try:
            self.url_name
        except NameError as e:
            logger.info(
                "SWREACTXBlock save() self.url_name was undefined: {e}".format(e=e)
            )
            self.url_name = "NONE"
        if self.url_name in ("", "NONE"):
            self.url_name = str(uuid.uuid4().hex)
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save() defined self.url_name as {s}".format(
                        s=self.url_name
                    )
                )
        else:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save() there is an existing url_name {s}".format(
                        s=self.url_name
                    )
                )
        try:
            XBlock.save(self)  # Call parent class save()
        # pylint: disable=W0718
        except Exception as e:
            logger.info("SWREACTXBlock save() had an error: {e}".format(e=e))
        if DEBUG:
            logger.info(
                "SWREACTXBlock save() back from parent save. self.swreact_results={s}".format(
                    s=self.swreact_results
                )
            )

    @XBlock.json_handler
    def get_data(self, msg, suffix=""):
        """RETURN DATA FOR THIS QUESTION."""
        if DEBUG:
            logger.info("SWREACTXBlock get_data() entered. msg={msg}".format(msg=msg))

        if self.my_max_attempts is None:
            self.my_max_attempts = -1

        # if DEBUG: logger.info("SWREACTXBlock get_data() self.solution={a}".format(a=self.solution))

        # NOTE: swreact app does not need to be passed the solution
        #       to our previous attempt at this problem
        data = {
            "question": self.question,
            "grade": self.grade,
            # "solution" : {},
            "count_attempts": self.count_attempts,
            "variants_count": self.variants_count,
            "max_attempts": self.my_max_attempts,
        }
        if DEBUG:
            logger.info("SWREACTXBlock get_data() data={d}".format(d=data))
        json_data = json.dumps(data)
        return json_data

    # @XBlock.json_handler
    def save_grade(self, data, suffix=""):
        """We're just calling it directly now, not in a callback."""
        if DEBUG:
            logger.info("SWREACTXBlock save_grade() entered")
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_grade() self.max_attempts={a}".format(
                    a=self.max_attempts
                )
            )

        # Check for missing grading attributes

        if DEBUG:
            logger.info("SWREACTXBlock save_grade() initial self={a}".format(a=self))
        if DEBUG:
            logger.info("SWREACTXBlock save_grade() initial data={a}".format(a=data))

        try:
            swreact_results = self.swreact_results
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.swreact_results was not defined: {e}".format(
                        e=e
                    )
                )
            swreact_results = ""

        try:
            q_weight = self.q_weight
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.q_weight was not defined: {e}".format(
                        e=e
                    )
                )
            q_weight = 1.0

        try:
            q_grade_showme_ded = self.q_grade_showme_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.q_grade_showme_dev was not defined: {e}".format(
                        e=e
                    )
                )
            q_grade_showme_ded = -1

        try:
            q_grade_hints_count = self.q_grade_hints_count
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.q_grade_hints_count was not defined: {e}".format(
                        e=e
                    ),
                )
            q_grade_hints_count = -1

        try:
            q_grade_hints_ded = self.q_grade_hints_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.q_grade_hints_ded was not defined: {e}".format(
                        e=e
                    )
                )
            q_grade_hints_ded = -1

        try:
            q_grade_errors_count = self.q_grade_errors_count
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.q_grade_errors_count was not defined: {e}".format(
                        e=e
                    )
                )
            q_grade_errors_count = -1

        try:
            q_grade_errors_ded = self.q_grade_errors_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.q_grade_errors_ded was not defined: {e}".format(
                        e=e
                    )
                )
            q_grade_errors_ded = -1

        try:
            q_grade_min_steps_count = self.q_grade_min_steps_count
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.q_grade_min_steps_count was not defined: {e}".format(
                        e=e
                    )
                )
            q_grade_min_steps_count = -1

        try:
            q_grade_min_steps_ded = self.q_grade_min_steps_ded
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.q_grade_min_steps_ded was not defined: {e}".format(
                        e=e
                    )
                )
            q_grade_min_steps_ded = -1

        try:
            q_grade_app_key = self.q_grade_app_key
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() self.q_grade_app_key was not defined: {e}".format(
                        e=e
                    )
                )
            q_grade_app_key = "SBIRPhase2"

        # Apply grading defaults

        if q_weight == -1:
            if DEBUG:
                logger.info("SWREACTXBlock save_grade() weight set to 1.0")
            q_weight = 1.0
        if q_grade_showme_ded == -1:
            if DEBUG:
                logger.info("SWREACTXBlock save_grade() showme default set to 3.0")
            q_grade_showme_ded = 3.0
        if q_grade_hints_count == -1:
            if DEBUG:
                logger.info("SWREACTXBlock save_grade() hints_count default set to 2")
            q_grade_hints_count = 2
        if q_grade_hints_ded == -1:
            if DEBUG:
                logger.info("SWREACTXBlock save_grade() hints_ded default set to 1.0")
            q_grade_hints_ded = 1.0
        if q_grade_errors_count == -1:
            if DEBUG:
                logger.info("SWREACTXBlock save_grade() errors_count default set to 3")
            q_grade_errors_count = 3
        if q_grade_errors_ded == -1:
            if DEBUG:
                logger.info("SWREACTXBlock save_grade() errors_ded default set to 1.0")
            q_grade_errors_ded = 1.0
        if q_grade_min_steps_ded == -1:
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() min_steps_ded default set to 0.25"
                )
            q_grade_min_steps_ded = 0.25
        if q_grade_app_key == "":
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_grade() app_key default set to SBIRPhase2"
                )
            q_grade_app_key = "SBIRPhase2"

        # Track whether they've completed it or not and assign 1.0 points if they have completed the problem
        if self.is_answered:
            grade = 1.0
        else:
            grade = 0.0

        self.raw_earned = grade

        if DEBUG:
            logger.info(
                "SWREACTXBlock save_grade() raw_earned={a}".format(a=self.raw_earned)
            )

        if DEBUG:
            logger.info("SWREACTXBlock save_grade() final data={a}".format(a=data))
        self.grade = grade
        if DEBUG:
            logger.info("SWREACTXBlock save_grade() grade={a}".format(a=self.grade))

        # Don't increment attempts on save grade.  We want to increment them when the student starts
        # a question, not when they finish.  Otherwise people can start the question as many times
        # as they want as long as they don't finish it, then reload the page.
        # self.count_attempts += 1
        # make sure we've recorded this attempt, but it should have been done in start_attempt():
        try:
            if self.q_index != -1:
                self.variants_attempted = set.bit_set_one(
                    self.variants_attempted, self.q_index
                )
                if DEBUG:
                    logger.info(
                        "SWREACTXBlock save_grade() record variants_attempted for variant {v}".format(
                            v=self.q_index
                        )
                    )
                self.previous_variant = self.q_index
                if DEBUG:
                    logger.info(
                        "SWREACTXBlock save_grade() record previous_variant for variant {v}".format(
                            v=self.previous_variant
                        )
                    )
            else:
                if DEBUG:
                    logger.error(
                        "SWREACTXBlock save_grade record variants_attempted for variant -1"
                    )
        except (NameError, AttributeError) as e:
            if DEBUG:
                logger.warning(
                    "SWREACTXBlock save_grade() self.q_index was not defined: {e}".format(
                        e=e
                    )
                )

        self.save()  # Time to persist our state!!!

        self.publish_grade()  # Now publish our grade results to persist them into the grading database

        # if DEBUG: logger.info("SWREACTXBlock save_grade() final self={a}".format(a=self))
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_grade() final self.count_attempts={a}".format(
                    a=self.count_attempts
                )
            )
        # if DEBUG: logger.info("SWREACTXBlock save_grade() final self.solution={a}".format(a=self.solution))
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_grade() final self.grade={a}".format(a=self.grade)
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_grade() final self.weight={a}".format(a=self.weight)
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_grade() final self.variants_attempted={v}".format(
                    v=self.variants_attempted
                )
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_grade() final self.previous_variant={v}".format(
                    v=self.previous_variant
                )
            )

    @XBlock.json_handler
    def start_attempt(self, data, suffix=""):
        """START A NEW ATTEMPT."""
        if DEBUG:
            logger.info("SWREACTXBlock start_attempt() entered")
        if DEBUG:
            logger.info("SWREACTXBlock start_attempt() data={d}".format(d=data))
        if DEBUG:
            logger.info(
                "SWREACTXBlock start_attempt() self.count_attempts={c} max_attempts={m}".format(
                    c=self.count_attempts, m=self.max_attempts
                )
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock start_attempt() self.variants_attempted={v}".format(
                    v=self.variants_attempted
                )
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock start_attempt() self.previous_variant={v}".format(
                    v=self.previous_variant
                )
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock start_attempt() passed q_index={q}".format(
                    q=data["q_index"]
                )
            )
        self.count_attempts += 1
        if DEBUG:
            logger.info(
                "SWREACTXBlock start_attempt() updated self.count_attempts={c}".format(
                    c=self.count_attempts
                )
            )
        variant = data["q_index"]
        if DEBUG:
            logger.info("variant is {v}".format(v=variant))
        if self.bit_is_set(self.variants_attempted, variant):
            if DEBUG:
                logger.info("variant {v} has already been attempted!".format(v=variant))
        else:
            if DEBUG:
                logger.info(
                    "adding variant {v} to self.variants_attempted={s}".format(
                        v=variant, s=self.variants_attempted
                    )
                )
            self.variants_attempted = self.bit_set_one(self.variants_attempted, variant)
            if DEBUG:
                logger.info(
                    "checking bit_is_set {v}={b}".format(
                        v=variant,
                        b=self.bit_is_set(self.variants_attempted, variant),
                    )
                )
            self.previous_variant = variant
            if DEBUG:
                logger.info("setting previous_variant to {v}".format(v=variant))

        return_data = {
            "count_attempts": self.count_attempts,
        }
        if DEBUG:
            logger.info(
                "SWREACTXBlock start_attempt() done return_data={return_data}".format(
                    return_data=return_data
                )
            )
        json_data = json.dumps(return_data)
        return json_data

    # RESET: PICK A NEW VARIANT
    @XBlock.json_handler
    def retry(self, data, suffix=""):
        """Reset and pick a new variant."""
        if DEBUG:
            logger.info("SWREACTXBlock retry() entered")
        if DEBUG:
            logger.info("SWREACTXBlock retry() data={d}".format(d=data))
        if DEBUG:
            logger.info(
                "SWREACTXBlock retry() self.count_attempts={c} max_attempts={m}".format(
                    c=self.count_attempts, m=self.max_attempts
                )
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock retry() self.variants_attempted={v}".format(
                    v=self.variants_attempted
                )
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock retry() pre-pick_question q_index={v}".format(
                    v=self.question["q_index"]
                )
            )
        self.question = self.pick_variant()

        return_data = {
            "question": self.question,
        }

        if DEBUG:
            logger.info(
                "SWREACTXBlock retry() post-pick returning self.question={q} return_data={r}".format(
                    q=self.question, r=return_data
                )
            )
        json_data = json.dumps(return_data)
        return json_data

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        if DEBUG:
            logger.info("SWREACTXBlock workbench_scenarios() entered")
        return [
            (
                "SWREACTXBlock",
                """<swreactxblock/>
            """,
            ),
            (
                "Multiple SWREACTXBlock",
                """<vertical_demo>
                <swreactxblock/>
                <swreactxblock/>
                <swreactxblock/>
                </vertical_demo>
            """,
            ),
        ]

    def studio_view(self, context=None):
        """The STUDIO view of the SWREACTXBlock, shown to instructors when authoring courses."""
        if DEBUG:
            logger.info("SWREACTXBlock studio_view() entered.")
        html = self.resource_string("static/html/swreactxstudio.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/swreactxstudio.css"))
        frag.add_javascript(self.resource_string("static/js/src/swreactxstudio.js"))

        frag.initialize_js("SWREACTXStudio")
        return frag

    def author_view(self, context=None):
        """The AUTHOR view of the SWREACTXBlock, shown to instructors when previewing courses."""
        if DEBUG:
            logger.info("SWREACTXBlock author_view() entered")
        html = self.resource_string("static/html/swreactxauthor.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/swreactxauthor.css"))
        frag.add_javascript_url(
            "//cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.1/MathJax.js?config=TeX-MML-AM_HTMLorMML"
        )
        frag.add_javascript(self.resource_string("static/js/src/swreactxauthor.js"))

        if DEBUG:
            logger.info(
                "SWREACTXBlock SWREACTXAuthor author_view v={a}".format(a=self.q_definition)
            )

        # tell author_view how many variants are defined
        variants = 1

        if DEBUG:
            logger.info(
                "SWREACTXBlock SWREACTXAuthor author_view variants={a}".format(a=variants)
            )

        frag.initialize_js("SWREACTXAuthor", variants)
        return frag

    # SAVE QUESTION
    @XBlock.json_handler
    def save_question(self, data, suffix=""):
        if DEBUG:
            logger.info("SWREACTXBlock save_question() entered")
        if DEBUG:
            logger.info("SWREACTXBlock save_question() data={d}".format(d=data))
        self.q_max_attempts = int(data["q_max_attempts"])
        self.q_weight = float(data["q_weight"])
        if data["q_option_showme"].lower() == "true":
            self.q_option_showme = True
        else:
            self.q_option_showme = False
        if data["q_option_hint"].lower() == "true":
            self.q_option_hint = True
        else:
            self.q_option_hint = False
        self.q_grade_showme_ded = float(data["q_grade_showme_ded"])
        self.q_grade_hints_count = int(data["q_grade_hints_count"])
        self.q_grade_hints_ded = float(data["q_grade_hints_ded"])
        self.q_grade_errors_count = int(data["q_grade_errors_count"])
        self.q_grade_errors_ded = float(data["q_grade_errors_ded"])
        self.q_grade_min_steps_count = int(data["q_grade_min_steps_count"])
        self.q_grade_min_steps_ded = float(data["q_grade_min_steps_ded"])
        self.q_grade_app_key = str(data["q_grade_app_key"])

        self.q_id = data["id"]
        self.q_label = data["label"]
        self.q_stimulus = data["stimulus"]
        self.q_definition = data["definition"]
        self.q_type = data["qtype"]
        self.q_display_math = data["display_math"]
        self.q_hint1 = data["hint1"]
        self.q_hint2 = data["hint2"]
        self.q_hint3 = data["hint3"]
        self.q_swreact_problem = data["swreact_problem"]
        self.q_swreact_rank = data["swreact_rank"]
        self.q_swreact_invalid_schemas = data["swreact_invalid_schemas"]
        self.q_swreact_problem_hints = data["swreact_problem_hints"]

        self.display_name = "Step-by-Step React"

        # mcdaniel jul-2020: fix syntax error in print statement
        print(self.display_name)
        return {"result": "success"}

    # SWREACT FINAL RESULTS: Save the final results of the SWREACT React app as a stringified structure.
    @XBlock.json_handler
    def save_swreact_final_results(self, data, suffix=""):
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_swreact_final_results() data={d}".format(d=data)
            )
        self.swreact_results = json.dumps(data, separators=(",", ":"))
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_swreact_final_results() self.swreact_results={r}".format(
                    r=self.swreact_results
                )
            )
        self.is_answered = True  # We are now done
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_swreact_final_results() self.is_answered={r}".format(
                    r=self.is_answered
                )
            )
        self.save_grade(data)  # Includes publishing our results to persist them
        if DEBUG:
            logger.info("SWREACTXBlock save_swreact_final_results() back from save_grade")
        self.emit_completion(1.0)   # Report that we are complete
        if DEBUG:
            logger.info("SWREACTXBlock save_swreact_final_results() back from emit_completion(1.0)")
        return {"result": "success"}

    # SWREACT PARTIAL RESULTS: Save the interim results of the SWREACT React app as a stringified structure.
    @XBlock.json_handler
    def save_swreact_partial_results(self, data, suffix=""):
        if DEBUG:
            logger.info(
                "SWREACTXBlock save_swreact_partial_results() data={d}".format(d=data)
            )
        # NOTE: There seemed to be a bug in swpwr 1.9.216+ app for POWER probems where there is an immediate callback to save_swpwr_partial_results
        # right after a call to save_swpwr_final_results, so we ignore any partial calls once we've seen a final call
        if self.is_answered == True:
            if DEBUG:
                logger.info("SWREACTXBlock save_swreact_partial_results() ignoring partial results for completed problem")
            return {"result": "success"}
        else:
            self.swreact_results = json.dumps(data, separators=(",", ":"))
            self.is_answered = False  # We are not done yet
            if DEBUG:
                logger.info(
                    "SWREACTXBlock save_swreact_partial_results() self.swreact_results={r}".format(
                        r=self.swreact_results
                    )
                )
            self.save_grade(data)  # Includes publishing our results to persist them
            if DEBUG:
                logger.info("SWREACTXBlock save_swreact_partial_results() back from save_grade")
            self.emit_completion(0.0)   # Report that we are NOT complete
            if DEBUG:
                logger.info("SWREACTXBlock save_swreact_partial_results() back from emit_completion(0.0)")
            return {"result": "success"}

    # Do necessary overrides from ScorableXBlockMixin
    def has_submitted_answer(self):
        """Returns True if the problem has been answered by the runtime user."""
        if DEBUG:
            logger.info("SWREACTXBlock has_submitted_answer() entered")
            logger.info(
                "SWREACTXBlock has_submitted_answer() {a}".format(a=self.is_answered)
            )
        return self.is_answered

    def get_score(self):
        """Return a raw score already persisted on the XBlock.

        Should not
        perform new calculations.
        Returns:
            Score(raw_earned=float, raw_possible=float)
        """
        if DEBUG:
            logger.info("SWREACTXBlock get_score() entered")
            logger.info("SWREACTXBlock get_score() earned {e}".format(e=self.raw_earned))
        if DEBUG:
            logger.info("SWREACTXBlock get_score() max {m}".format(m=self.max_score()))
        return Score(float(self.raw_earned), float(self.max_score()))

    def set_score(self, score):
        """Persist a score to the XBlock.

        The score is a named tuple with a raw_earned attribute and a
        raw_possible attribute, reflecting the raw earned score and the maximum
        raw score the student could have earned respectively.
        Arguments:
            score: Score(raw_earned=float, raw_possible=float)
        Returns:
            None
        """
        if DEBUG:
            logger.info("SWREACTXBlock set_score() earned {e}".format(e=score.raw_earned))
        self.raw_earned = score.raw_earned

    def calculate_score(self):
        """Calculate a new raw score based on the state of the problem.

        This method should not modify the state of the XBlock.
        Returns:
            Score(raw_earned=float, raw_possible=float)
        """
        if DEBUG:
            logger.info("SWREACTXBlock calculate_score() grade {g}".format(g=self.grade))
        if DEBUG:
            logger.info(
                "SWREACTXBlock calculate_score() max {m}".format(m=self.max_score)
            )
        return Score(float(self.grade), float(self.max_score()))

    def allows_rescore(self):
        """
        Boolean value: Can this problem be rescored?
        Subtypes may wish to override this if they need conditional support for
        rescoring.
        """
        if DEBUG:
            logger.info("SWREACTXBlock allows_rescore() False")
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
        """Returns the block's current saved grade multiplied by the block's weight- the number of points earned by the
        learner."""
        if DEBUG:
            logger.info(
                "SWREACTXBlock weighted_grade() earned {e}".format(e=self.raw_earned)
            )
        if DEBUG:
            logger.info(
                "SWREACTXBlock weighted_grade() weight {w}".format(w=self.q_weight)
            )
        return self.raw_earned * self.q_weight

    def bit_count_ones(self, var):
        """Returns the count of one bits in an integer variable Note that Python ints are full-fledged objects, unlike
        in C, so ints are plenty long for these operations."""
        if DEBUG:
            logger.info("SWREACTXBlock bit_count_ones var={v}".format(v=var))
        count = 0
        bits = var
        for b in range(32):
            lsb = (bits >> b) & 1
            count = count + lsb
        if DEBUG:
            logger.info("SWREACTXBlock bit_count_ones result={c}".format(c=count))
        return count

    def bit_set_one(self, var, bitnum):
        """Return var = var with bit 'bitnum' set Note that Python ints are full-fledged objects, unlike in C, so ints
        are plenty long for these operations."""
        if DEBUG:
            logger.info(
                "SWREACTXBlock bit_set_one var={v} bitnum={b}".format(v=var, b=bitnum)
            )
        var = var | (1 << bitnum)
        if DEBUG:
            logger.info("SWREACTXBlock bit_set_one result={v}".format(v=var))
        return var

    def bit_is_set(self, var, bitnum):
        """Return True if bit bitnum is set in var Note that Python ints are full-fledged objects, unlike in C, so ints
        are plenty long for these operations."""
        if DEBUG:
            logger.info(
                "SWREACTXBlock bit_is_set var={v} bitnum={b}".format(v=var, b=bitnum)
            )
        result = var & (1 << bitnum)
        if DEBUG:
            logger.info(
                "SWREACTXBlock bit_is_set result={v} b={b}".format(
                    v=result, b=bool(result)
                )
            )
        return bool(result)

    def pick_variant(self):
        # pick_variant() selects one of the available question variants that we have not yet attempted.
        # If there is only one variant left, we have to return that one.
        # If there are 2+ variants left, do not return the same one we started with.
        # If we've attempted all variants, we clear the list of attempted variants and pick again.
        #  Returns the question structure for the one we will use this time.

        try:
            prev_index = self.q_index
        except (NameError, AttributeError):
            prev_index = -1

        if DEBUG:
            logger.info(
                "SWREACTXBlock pick_variant() started replacing prev_index={p}".format(
                    p=prev_index
                )
            )

        # If there's no self.q_index, then this is our first look at this question in this session, so
        # use self.previous_variant if we can.  This won't restore all previous attempts, but makes sure we
        # don't use the variant that is displayed in the student's last attempt data.
        if prev_index == -1:
            try:  # use try block in case attribute wasn't saved in previous student work
                prev_index = self.previous_variant
                if DEBUG:
                    logger.info(
                        "SWREACTXBlock pick_variant() using previous_variant for prev_index={p}".format(
                            p=prev_index
                        )
                    )
            except (NameError, AttributeError) as e:
                if DEBUG:
                    logger.info(
                        "SWREACTXBlock pick_variant() self.previous_variant does not exist. Using -1: {e}".format(
                            e=e
                        )
                    )
                prev_index = -1

        if self.bit_count_ones(self.variants_attempted) >= self.variants_count:
            if DEBUG:
                logger.warning(
                    "SWREACTXBlock pick_variant() seen all variants attempted={a} count={c}, clearing variants_attempted".format(
                        a=self.variants_attempted, c=self.variants_count
                    )
                )
            self.variants_attempted = 0  # We have not yet attempted any variants

        tries = 0  # Make sure we dont try forever to find a new variant
        max_tries = 100

        if self.variants_count <= 0:
            if DEBUG:
                logger.warning(
                    "SWREACTXBlock pick_variant() bad variants_count={c}, setting to 1.".format(
                        c=self.variants_count
                    )
                )
            self.variants_count = 1

        while tries < max_tries:
            tries = tries + 1
            q_randint = random.randint(
                0, ((self.variants_count * 100) - 1)
            )  # 0..999 for 10 variants, 0..99 for 1 variant, etc.
            if DEBUG:
                logger.info(
                    "SWREACTXBlock pick_variant() try {t}: q_randint={r}".format(
                        t=tries, r=q_randint
                    )
                )

            if q_randint >= 0 and q_randint < 100:
                q_index = 0
            elif q_randint >= 100 and q_randint < 200:
                q_index = 1
            elif q_randint >= 200 and q_randint < 300:
                q_index = 2
            elif q_randint >= 300 and q_randint < 400:
                q_index = 3
            elif q_randint >= 400 and q_randint < 500:
                q_index = 4
            elif q_randint >= 500 and q_randint < 600:
                q_index = 5
            elif q_randint >= 600 and q_randint < 700:
                q_index = 6
            elif q_randint >= 700 and q_randint < 800:
                q_index = 7
            elif q_randint >= 800 and q_randint < 900:
                q_index = 8
            else:
                q_index = 9

            # If there are 2+ variants left and we have more tries left, do not return the same variant we started with.
            if (
                q_index == prev_index
                and tries < max_tries
                and self.bit_count_ones(self.variants_attempted)
                < self.variants_count - 1
            ):
                if DEBUG:
                    logger.info(
                        "SWREACTXBlock pick_variant() try {t}: with bit_count_ones(variants_attempted)={v} < variants_count={c}-1 we won't use the same variant {q} as prev variant".format(
                            t=tries,
                            v=self.bit_count_ones(self.variants_attempted),
                            c=self.variants_count,
                            q=q_index,
                        )
                    )
                break

            if not self.bit_is_set(self.variants_attempted, q_index):
                if DEBUG:
                    logger.info(
                        "SWREACTXBlock pick_variant() try {t}: found unattempted variant {q}".format(
                            t=tries, q=q_index
                        )
                    )
                break
            if DEBUG:
                logger.info(
                    "pick_variant() try {t}: variant {q} has already been attempted".format(
                        t=tries, q=q_index
                    )
                )
            if self.bit_count_ones(self.variants_attempted) >= self.variants_count:
                if DEBUG:
                    logger.info(
                        "pick_variant() try {t}: we have attempted all {c} variants. clearning self.variants_attempted.".format(
                            t=tries, c=self.bit_count_ones(self.variants_attempted)
                        )
                    )
                q_index = 0  # Default
                self.variants_attempted = 0
                break

        if tries >= max_tries:
            if DEBUG:
                logger.error(
                    "pick_variant() could not find an unattempted variant of {l} in {m} tries! clearing self.variants_attempted.".format(
                        l=self.q_label, m=max_tries
                    )
                )
            q_index = 0  # Default
            self.variants_attempted = 0

        if DEBUG:
            logger.info("pick_variant() Selected variant {v}".format(v=q_index))

        # Note: we won't set self.variants_attempted for this variant until they
        # actually begin work on it (see start_attempt() below)

        question = {
            "q_id": self.q_id,
            "q_user": self.xb_user_username,
            "q_index": 0,
            "q_label": self.q_label,
            "q_stimulus": self.q_stimulus,
            "q_definition": self.q_definition,
            "q_type": self.q_type,
            "q_display_math": self.q_display_math,
            "q_hint1": self.q_hint1,
            "q_hint2": self.q_hint2,
            "q_hint3": self.q_hint3,
            "q_swreact_problem": self.q_swreact_problem,
            "q_swreact_rank": self.q_swreact_rank,
            "q_swreact_invalid_schemas": self.q_swreact_invalid_schemas,
            "q_swreact_problem_hints": self.q_swreact_problem_hints,
            "q_weight": self.my_weight,
            "q_max_attempts": self.my_max_attempts,
            "q_option_hint": self.my_option_hint,
            "q_option_showme": self.my_option_showme,
            "q_grade_showme_ded": self.my_grade_showme_ded,
            "q_grade_hints_count": self.my_grade_hints_count,
            "q_grade_hints_ded": self.my_grade_hints_ded,
            "q_grade_errors_count": self.my_grade_errors_count,
            "q_grade_errors_ded": self.my_grade_errors_ded,
            "q_grade_min_steps_count": self.my_grade_min_steps_count,
            "q_grade_min_steps_ded": self.my_grade_min_steps_ded,
            "q_grade_app_key": self.my_grade_app_key,
        }

        if DEBUG:
            logger.info(
                "SWREACTXBlock pick_variant() returned question q_index={i} question={q}".format(
                    i=question["q_index"], q=question
                )
            )
        return question
