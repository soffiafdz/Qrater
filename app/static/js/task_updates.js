// Update tasks progress in HTTP
function setTaskProgress(task_id, progress) {
  $('#' + task_id + 'Progress').text(progress + "%");
  $('#' + task_id + 'ProgressBar').attr("style", "width: " + progress + "%");
  $('#' + task_id + 'ProgressBar').attr("aria-valuenow", progress);
}

// Read task progress from notifications
function updateProgress() {
  $.ajax('/notifications').done(
    function(notifications) {
      let task_progress = 100;
      for (let i = 0; i < notifications.length; i++) {
        if (notifications[i].name.includes('_progress')) {
          task_progress = notifications[i].data.progress;
          setTaskProgress(notifications[i].data.task_id, task_progress);
          readTaskAlerts();
        }
      }
      if (task_progress != 100){
        setTimeout(updateProgress, 1000);
      }
    }
  );
}

// Read task notifications and send them to HTTP
function readTaskAlerts() {
  $.ajax('/notifications').done(
    function(notifications) {
      for (let i = 0; i < notifications.length; i++) {
        if (notifications[i].name.includes('_alert')) {
          let flashMessage = `
<div
  class="alert alert-${notifications[i].data.color} alert-dismissible fade show"
  role="alert"
  >
  <svg
    class="bi flex=shrink-0 me-2"
    width="24"
    height="24"
    role="img"
    >
    <use xlink:href="${notifications[i].data.icon}"/>
  </svg>${notifications[i].data.message}
  <button
    type="button"
    class="btn-close"
    data-bs-dismiss="alert"
    aria-label="Close"
    ></button>
</div>`;
          console.log('Loaded flash message');
          $('#flashedMessages').prepend(flashMessage);
          $.ajax(
            '/notifications?name=' + notifications[i].name,
            {type: 'DELETE'}
          );
        }
      }
    }
  );
}

// Runc at the start
$(function() {
  setTimeout(updateProgress, 1000);
});
