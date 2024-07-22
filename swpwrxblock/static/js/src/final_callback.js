
      // global array for storing the SWPWR problems in the assignment

      //NOTYET window.swpwr_problems = [];

      // Final callback to submit SWPWR React app results

      returnPowerResults(solution){
        console.info("returnPowerResults solution",solution);
        var solution_string = JSON.stringify(solution);
        console.info("returnPowerResults solution string",solution_string);
        $.ajax({
          type: "POST",
          url: handlerUrlSwpwrResults,
          data: solution_string,
          success: function (data,msg) {
            console.info("returnPowerResults solution POST success");
            console.info("returnPowerResults solution POST data",data);
            console.info("returnPowerResults solution POST ",msg);
          },
          error: function(XMLHttpRequest, textStatus, errorThrown) {
            console.info("returnPowerResults solution POST error textStatus=",textStatus," errorThrown=",errorThrown);
          }
        });
        // Hide the React app and show the problem complete msg
        // $('.SWPowerComponent').hide();  // Hide React app root div
        $('.problem-complete').show();  // Show the 'problem is complete' message
        $('.sequence-bottom').show();   // Show the problem navigation buttons again
      };

