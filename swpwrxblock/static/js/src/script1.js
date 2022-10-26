      var callbacks = {
        success: celebrate,
        status: updateProgress,
      };

      var options = {
        hideMenu: true,
        scribbles: false,
      };

      function saveProgress() {
        console.dir(querium.saveState());
      }

      function updateProgress(stats) {
        console.log("updatingProgress in webApp");
        console.dir(stats);
      }

      querium.appID = "SW4WPapp";
      querium.student = "SW4WPuser";
      console.log("querium.student = " + querium.student);
      querium.options = options;
