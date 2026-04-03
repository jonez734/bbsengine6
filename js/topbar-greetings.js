/**
 * topbar-greetings.js - Update greetings in topbar
 * @description Polls for user greeting changes
 */
$(document).ready(function() {
  'use strict';

  const UPDATE_INTERVAL_MS = 5000;

  const be = bbsengine();
  if (!be) {
    console.error("topbar-greetings.100: bbsengine() returned null");
    return;
  }

  be.gettopbarupdateinterval().then(function(interval) {
    be.addinterval(interval, "update topbar.greetings", function() {
      be.updatetopbaritem("topbar.greetings", ".greetings");
    });
  }).catch(function(err) {
    console.error("topbar-greetings.110: error getting interval:", err);
  });
});