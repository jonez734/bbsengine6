$(document).ready(function() {
  be.addinterval(5000, "update topbar.loginlogout", function() {
    be.updatetopbaritem("topbar.loginlogout", $("div#topbar .loginlogout"), "/get-topbar-loginlogout?callback=?");
  });
}); /* end document.ready() */
