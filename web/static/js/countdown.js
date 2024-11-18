/*
use this to display a countdown timer
constructor expects the name of a container to update with the countdown info
implementing class should call "reset_countdown()" to reset the timer to 0

start countdown with call to start_countdown()
*/

class UpdateCountdown {

  constructor(target_div, expected_update = 15, stale_class = 'text-danger'){
    this.UPDATE_COUNTDOWN = 0;
    this.TARGET_DIV = target_div;  // div to update countdown info
    this.RESET_TIMEOUT = expected_update;  // expected amount of time before reset
    this.STALE_CLASSNAME = stale_class;
  }

  start_countdown(){
    setInterval(this.show_countdown.bind(this), 1000);
  }

  show_countdown(){
    this.UPDATE_COUNTDOWN ++;
    $(`#${this.TARGET_DIV}`).html(this.UPDATE_COUNTDOWN);

    if(this.UPDATE_COUNTDOWN > this.RESET_TIMEOUT)
    {
      $(`#${this.TARGET_DIV}`).addClass(this.STALE_CLASSNAME);
    }
  }

  reset_countdown(){
    // reset countdown and remove stale class (if exists)
    this.UPDATE_COUNTDOWN = 0;
    $(`#${this.TARGET_DIV}`).removeClass(this.STALE_CLASSNAME);
  }

}
