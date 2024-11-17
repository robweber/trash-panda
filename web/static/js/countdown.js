/*
use this to display a countdown timer
page must contain an element "last_updated" to display the countdown in seconds
implementing class should call "reset_countdown()" to reset the timer to 0

start countdown with call to start_countdown()
*/

class UpdateCountdown {

  constructor(){
    this.UPDATE_COUNTDOWN = 0;
  }

  start_countdown(){
    setInterval(this.show_countdown.bind(this), 1000);
  }

  show_countdown(){
    this.UPDATE_COUNTDOWN ++;
    $('#last_updated').html(this.UPDATE_COUNTDOWN);
  }

  reset_countdown(){
    this.UPDATE_COUNTDOWN = 0;
  }

}
