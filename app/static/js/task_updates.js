// Update tasks progress in HTTP
function setTaskProgress(task_id, progress) {
  $('#' + task_id + 'Progress').text(progress + "%");
  $('#' + task_id + 'ProgressBar').attr("style", "width: " + progress + "%");
  $('#' + task_id + 'ProgressBar').attr("aria-valuenow", progress);
}

// Update task progress from a notification
function updateProgress(notification) {
  let taskProgress = notification.data.progress;
  setTaskProgress(notification.data.task_id, taskProgress);
}

// Write alert into HTTP from notification
function setAlert(icon, color, message) {
  let flashMessage = `<div
  class="alert alert-${color} alert-dismissible fade show"
  role="alert"
  >
  <svg
    class="bi flex=shrink-0 me-2"
    width="24"
    height="24"
    role="img"
    >
    <use xlink:href="${icon}"/>
  </svg>${message}
  <button
    type="button"
    class="btn-close"
    data-bs-dismiss="alert"
    aria-label="Close"
    ></button>
</div>`;

  // Show alert
  $('#flashedMessages').prepend(flashMessage);

}

// Delete from database
function deleteAlert(name) {
  $.ajax('/notifications?name=' + name, {type: 'DELETE'});
}

// Parse notifications
function readNotifications(since, timer) {
  $.ajax('/notifications?since=' + since).done(
    function(notifications) {
      for (let i = 0; i < notifications.length; i++) {
        since = notifications[i].timestamp;
        if (notifications[i].name.includes('_progress'))
          updateProgress(notifications[i]);

        if (notifications[i].name.includes('_alert')) {
          setAlert(
            notifications[i].data.icon,
            notifications[i].data.color,
            notifications[i].data.message
          );
          deleteAlert(notifications[i].name);
        }
      }
        //If there are not new notifications increment wait time; else reset it
        let newTimer
        if (notifications.length > 0) {
          newTimer = 1000
        } else {
          newTimer = timer + 1000
        }
        setTimeout(readNotifications, newTimer, since, newTimer)
    }
  );
}

// Runc at the start
$(function() {
  // Wait one second before first run, so notifications load in server
  setTimeout(readNotifications, 1000, 0, 1000);
});
