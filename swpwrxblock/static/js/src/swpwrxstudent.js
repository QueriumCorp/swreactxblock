/* Javascript for SWPWRXBlock.
 * TODO:  Enforce assignment due date for not starting another attempt.
 *        Disble Hint and ShowMe buttons if options are set.
 */

var handlerUrlSwpwrResults;  // Define this globally where it can be found by the React swpwr onSubmit code

function SWPWRXStudent(runtime, element) {

    console.info("SWPWRXStudent start");
    console.info("SWPWRXStudent element",element);

    var handlerUrlGetData = runtime.handlerUrl(element, 'get_data');

    handlerUrlSwpwrResults = runtime.handlerUrl(element, 'save_swpwr_results');   // Leave a handlerUrl for the SWPWR onSubmit callback

    console.info("SWPWRXStudent calling get_data at ",handlerUrlGetData);

    const SWPHASE = 5;          // Which element of the POWER steps array in window.swpwr_problem contains the StepWise UI?

    get_data_data = {}		// don't need to sent any data to get_data
        
    $.ajax({
        type: "POST",
        url: handlerUrlGetData,
        data: JSON.stringify(get_data_data),
        error: function(XMLHttpRequest, textStatus, errorThrown) { 
               console.info("SWPWRXstudent get_data POST error textStatus=",textStatus," errorThrown=",errorThrown);
               // alert("Status: " + textStatus); alert("Error: " + errorThrown); 
        },
        success: function (data,msg) {
            console.info("SWPWRXstudent GET success");
            console.info("SWPWRXstudent GET data",data);
            console.info("SWPWRXstudent GET msg",msg);

            var data_obj = JSON.parse(data);
            console.info("SWPWRXstudent GET data_obj",data_obj);

            // Set our context variables from the data we receive
            var question = data_obj.question;
            var grade = data_obj.grade;
            var solution = data_obj.solution;
            var count_attempts = data_obj.count_attempts;
            var variants_count = data_obj.variants_count;
            var max_attempts = data_obj.max_attempts;
            var enable_showme = question.q_option_showme;
            var enable_hint = question.q_option_hint;
            var weight = question.q_weight;
            var min_steps = question.q_grade_min_steps_count;
            var min_steps_ded = question.q_grade_min_steps_ded;
            var swpwr_string = question.swpwr_string;
        
            console.info("SWPWRXStudent question",question);
            // console.info("SWPWRXStudent enable_showme",enable_showme);
            // console.info("SWPWRXStudent enable_hint",enable_hint);
            console.info("SWPWRXStudent solution",solution);
            console.info("SWPWRXStudent count_attempts",count_attempts);
            console.info("SWPWRXStudent variants_counnt",variants_count);
            console.info("SWPWRXStudent max_attempts",max_attempts);
            console.info("SWPWRXStudent weight ",weight);
            console.info("SWPWRXStudent min steps",min_steps);
            console.info("SWPWRXStudent min steps dec",min_steps_ded);
            console.info("SWPWRXStudent grade",grade);
        
            // Replace the stepwise-related fields in the SWPR React problem template with the StepWise values from the Xblock attributes

            console.info("SWPWRXStudent window.swpwr_problem original",window.swpwr_problem);
            // window.swpwr_problem.stimulus = `A blue mountain bike is on sale for $399. Its regular price is $650.
            //       What is the difference between the regular price and the sale price?`;
            console.info("SWPWRXStudent question.q_swpwr_string",question.q_swpwr_string);
            window.swpwr_problem.stimulus = question.q_swpwr_string;
            console.info("SWPWRXStudent window.swpwr_problem.stimulus",window.swpwr_problem.stimulus);
            console.info("SWPWRXStudent question",question);

            // StepWise problem data goes in swpwr_problem.steps[SWPHASE]
            console.info("SWPWRXStudent window.swpwr_problem.steps[SWPHASE] original",window.swpwr_problem.steps[SWPHASE]);
            window.swpwr_problem.steps[SWPHASE].swlabel = question.q_label;
            window.swpwr_problem.steps[SWPHASE].description = question.q_stimulus;
            window.swpwr_problem.steps[SWPHASE].definition = question.q_definition;
            window.swpwr_problem.steps[SWPHASE].swtype = question.q_type;
            window.swpwr_problem.steps[SWPHASE].hint1 = question.q_hint1;
            window.swpwr_problem.steps[SWPHASE].hint2 = question.q_hint2;
            window.swpwr_problem.steps[SWPHASE].hint3 = question.q_hint3;
            console.info("SWPWRXStudent window.swpwr_problem.steps[SWPHASE] modified",window.swpwr_problem.steps[SWPHASE]);

            console.info("SWPWRXStudent window.swpwr_problem modified",window.swpwr_problem);
        
            if (typeof enable_showme === 'undefined') {
                // console.info("enable_showme is undefined");
                enable_showme = true;
            };
            if (typeof enable_hint === 'undefined') {
                // console.info("enable_hint is undefined");
                enable_hint = true;
            };
        
            var handlerUrl = runtime.handlerUrl(element, 'save_grade');
            console.info("SWPWRXStudent handlerUrl",handlerUrl);
            var handlerUrlStart = runtime.handlerUrl(element, 'start_attempt');
            console.info("SWPWRXStudent handlerUrlStart",handlerUrlStart);
            var handlerUrlRetry = runtime.handlerUrl(element, 'retry');
            console.info("SWPWRXStudent handlerUrlRetry",handlerUrlRetry);

            // Get Primary Element Handles
            var swpwrxblock_block = $('.swpwrxblock_block', element)[0];
            var stepwise_element = $('querium', element)[0];
        
            // set student id
            var sId = ( question.q_user.length>1 ? question.q_user : "UnknownStudent");
        
            // console.info( sId );
        
            /* PAGE LOAD EVENT */
            $(function ($) {
            });
        
            // wrap element as core.js may pass a raw element or an wrapped one
            angular.bootstrap($(element), ['querium-stepwise']);
            MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
       }
    });
    console.info("SWPWRXStudent end");
    $('.loading-box').show();        // Show loading box while we wait
}
