$(document).ready(function() {
  'use strict';
  const be = bbsengine();
  if (!be) {
    console.error("topbar-greetings.js: bbsengine() returned null");
    return;
  }
  
  be.gettopbarupdateinterval().then(function(interval) {
    be.addinterval(interval, "topbar.greetings");
    be.addinterval(5000, "update topbar.greetings", function() {
      be.updatetopbaritem("topbar.greetings", ".greetings");
    });
  }).catch(function(err) {
    console.error("topbar-greetings.js: error getting interval:", err);
  });
});
