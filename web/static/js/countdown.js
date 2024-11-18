/*
use this to display a countdown timer
page must contain an element "last_updated" to display the countdown in seconds
implementing class should call "reset_countdown()" to reset the timer to 0

start countdown with call to start_countdown()
*/

class UpdateCountdown {

  constructor(target_div){
    this.UPDATE_COUNTDOWN = 0;
    this.TARGET_DIV = target_div;  // div to update countdown info
  }

  start_countdown(){
    setInterval(this.show_countdown.bind(this), 1000);
  }

  show_countdown(){
    this.UPDATE_COUNTDOWN ++;
    $(`#${this.TARGET_DIV}`).html(this.UPDATE_COUNTDOWN);
  }

  reset_countdown(){
    this.UPDATE_COUNTDOWN = 0;
  }

}
