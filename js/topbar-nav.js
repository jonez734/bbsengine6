/**
 * topbar-nav.js - Update navigation in topbar
 * @description Polls for navigation changes
 */
$(document).ready(function() {
  'use strict';

  const UPDATE_INTERVAL_MS = 5000;

  const be = bbsengine();
  if (!be) {
    console.error("topbar-nav.100: bbsengine() returned null");
    return;
  }

  be.addinterval(UPDATE_INTERVAL_MS, "update nav", function() {
    be.updatetopbaritem("nav", ".blurb .nav");
  });
});