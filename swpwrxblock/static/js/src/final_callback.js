
      // global array for storing the SWPWR problems in the assignment

      window.swpwr_problems = [];

      // Final callback to submit SWPWR React app results

      window.swpwr_onSubmit = (solution) =>{
        console.info("swpwr_onSubmit solution",solution);
        var solution_string = JSON.stringify(solution);
        console.info("swpwr_onSubmit solution string",solution_string);
        $.ajax({
          type: "POST",
          url: handlerUrlSwpwrResults,
          data: solution_string,
          success: function (data,msg) {
            console.info("swpwr_onSubmit solution POST success");
            console.info("swpwr_onSubmit solution POST data",data);
            console.info("swpwr_onSubmit solution POST ",msg);
          },
          error: function(XMLHttpRequest, textStatus, errorThrown) {
            console.info("swpwr_onSubmit solution POST error textStatus=",textStatus," errorThrown=",errorThrown);
          }
        });
        // Hide the React app and show the problem complete msg
        $('.swpwrReact').hide();        // Hide React app root div
        $('.problem-complete').show();  // Show the 'problem is complete' message
      };

