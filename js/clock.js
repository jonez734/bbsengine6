/**
 * clock.js - Real-time clock display
 * @description Updates clock every second with flashing colon effect
 */
$(document).ready(function() {
  'use strict';

  /** @type {number} - Update interval in milliseconds */
  const UPDATE_INTERVAL_MS = 1000;

  /** @type {boolean} - Colon visibility state */
  let colonVisible = true;

  const be = bbsengine();
  if (!be) {
    console.error("clock.100: bbsengine() returned null");
    return;
  }

  const $clock = $("#clock");
  if ($clock.length === 0) {
    return;
  }

  be.addinterval(UPDATE_INTERVAL_MS, "clock", updateclock);

  function updateclock() {
    const currentTime = new Date();

    let currentHours = currentTime.getHours();
    let currentMinutes = currentTime.getMinutes();

    currentMinutes = (currentMinutes < 10 ? "0" : "") + currentMinutes;

    const meridian = (currentHours < 12) ? "AM" : "PM";

    currentHours = (currentHours > 12) ? currentHours - 12 : currentHours;
    currentHours = (currentHours === 0) ? 12 : currentHours;

    const $flashingColon = $clock.find(".flashingcolon");
    if ($flashingColon.length > 0) {
      $flashingColon.css("visibility", colonVisible ? "visible" : "hidden");
      colonVisible = !colonVisible;
    }

    $clock.find(".currenthours").html(currentHours);
    $clock.find(".currentminutes").html(currentMinutes);
    $clock.find(".meridian").html(meridian);
  }
});