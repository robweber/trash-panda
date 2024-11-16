/*
use this to display a countdown timer
page must contain an element "update_countdown" to display the countdown in seconds
implementing class should call "reset_countdown()" to reset the timer to 0

start countdown with call to start_countdown()
*/

UPDATE_COUNTDOWN = 0;

function start_countdown(){
  setInterval(show_countdown, 1000);
}

function show_countdown(){
  UPDATE_COUNTDOWN ++;
  $('#last_updated').html(UPDATE_COUNTDOWN);
}

function reset_countdown(){
  UPDATE_COUNTDOWN = 0;
}
