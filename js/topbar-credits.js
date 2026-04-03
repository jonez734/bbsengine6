/**
 * topbar-credits.js - Update credit count in topbar
 * @description Polls for credit count changes
 */
$(document).ready(function() {
  'use strict';

  const UPDATE_INTERVAL_MS = 5000;

  const be = bbsengine();
  if (!be) {
    console.error("topbar-credits.100: bbsengine() returned null");
    return;
  }

  be.addinterval(UPDATE_INTERVAL_MS, "update credit count", function() {
    be.updatetopbaritem("topbar.credits", ".credits");
  });
});