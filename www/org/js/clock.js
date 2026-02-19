$(document).ready(function () {
  var foo = 1;

  let be = getbbsengine();
  console.log("be="+JSON.stringify(be));
  
  be.addinterval(1000, "clock", updateclock);

  function updateclock()
  {
    var currentTime = new Date();
      
    var currentHours = currentTime.getHours();
    var currentMinutes = currentTime.getMinutes();

    // http://stackoverflow.com/a/15304657
    var currentTZ = currentTime.toString().match(/\(([A-Za-z\s].*)\)/)[1];
            
    // Pad the minutes and seconds with leading zeros, if required
    currentMinutes = (currentMinutes < 10 ? "0" : "") + currentMinutes;
                  
    // Choose either "AM" or "PM" as appropriate
    var meridian = (currentHours < 12) ? "AM" : "PM";
                      
    // Convert the hours component to 12-hour format if needed
    currentHours = (currentHours > 12) ? currentHours - 12 : currentHours;
    
    // Convert an hours component of "0" to "12"
    currentHours = (currentHours === 0) ? 12 : currentHours;
                              
    // Compose the string for display
//    colon = (foo == 1) ? " " : ":";
    if (foo === 0)
    {
      $("#clock .flashingcolon").css("visibility", "visible");
    }
    else
    {
      $("#clock .flashingcolon").css("visibility","hidden");
    }
//    var currentTimeString = "<span class=\"currenthours\">"+currentHours+"</span><span class=\"flashingcolon\">" + colon + "</span><span class=\"currentminutes\">"+currentMinutes + "</span> <span class=\"meridian\">" + meridian + "</span> <span class=\"currenttz\">" + currentTZ+"</span>";
    $("#clock .currenthours").html(currentHours);
    $("#clock .currentminutes").html(currentMinutes);
    $("#clock .meridian").html(meridian);
//    $("#clock .currenttz").html(currentTZ);
    // Update the time display
//    $("#clock").html(currentTimeString);
    foo = 1 - foo;
  }

/*
  $("#clock").removeClass("running");
  $("#clock").addClass("init");
  updateclock();
  $("#clock").switchClass("init", "running", 1500, "linear", function () {
    intervalid = setInterval(updateclock, 5000);
  });
*/
});
