 let isRecording = false;
  let selectedRating = 0;
  let uploadedFiles = [];

  /* PAGE NAVIGATION */
  function showPage(pageId, btn) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    document.getElementById(pageId).classList.add('active');
    if (btn) btn.classList.add('active');
  }

   /* ===========================
     ADMIN LOGIN & DASHBOARD
     =========================== */

  function adminLogin(event) {
    event.preventDefault();

    const username = document.getElementById("adminUsername").value;
    const password = document.getElementById("adminPassword").value;

    // Demo credentials
    if (username === "admin" && password === "admin123") {
      // Hide login
      document.getElementById("adminLogin").style.display = "none";

      // Show dashboard
      document.getElementById("adminDashboard").style.display = "block";

      showNotification("Admin login successful", "success");
    } else {
      showNotification("Invalid admin credentials", "error");
    }
  }

  function adminLogout() {
    // Clear fields
    document.getElementById("adminUsername").value = "";
    document.getElementById("adminPassword").value = "";

    // Hide dashboard
    document.getElementById("adminDashboard").style.display = "none";

    // Show login again
    document.getElementById("adminLogin").style.display = "block";

    showNotification("Logged out successfully", "success");
  }

function showPage(pageId) {

    // Hide all pages
    document.querySelectorAll('.page').forEach(function(page) {
        page.classList.remove('active');
    });

    // Show selected page
    document.getElementById(pageId).classList.add('active');

    // Remove active button
    document.querySelectorAll('.nav-btn').forEach(function(btn) {
        btn.classList.remove('active');
    });

    // Set active button
    event.target.classList.add('active');
}

  /* NOTIFICATION */

  function showNotification(message, type) {
    const note = document.getElementById('notification');
    note.textContent = message;
    note.className = `notification ${type}`;
    note.style.display = 'block';

    setTimeout(() => {
      note.style.display = 'none';
    }, 3000);
  }
  
  /* admin dashboard */

  function openModal(type, dob, date, text, phone) {
  document.getElementById("type").innerText = type;
  document.getElementById("dob").innerText = dob;
  document.getElementById("date").innerText = date;
  document.getElementById("text").innerText = text;
  document.getElementById("callBtn").href = "tel:" + phone;

  document.getElementById("modal").style.display = "block";
}

function closeModal() {
  document.getElementById("modal").style.display = "none";
}

/* user signup */

function validateSignup(){

    let name = document.getElementById("name").value;
    let mobile = document.getElementById("mobile").value;
    let dob = document.getElementById("dob").value;
    let aadhaar = document.getElementById("aadhaar").value;
    let email = document.getElementById("email").value;
    let password = document.getElementById("password").value;

    if(name === "" || mobile === "" || dob === "" || aadhaar === "" || email === "" || password === ""){
        alert("All fields are required");
        return false;
    }

    if(mobile.length !== 10){
        alert("Mobile number must be 10 digits");
        return false;
    }

    if(aadhaar.length !== 12){
        alert("Aadhaar number must be 12 digits");
        return false;
    }

    if(password.length < 6){
        alert("Password must be at least 6 characters");
        return false;
    }

    alert("Account Created Successfully (Backend connection needed)");
    return false;
}

/* complaint page */

let mediaRecorder;
let audioChunks = [];

async function toggleRecording() {

    const status = document.getElementById("recordingStatus");
    const voiceInput = document.getElementById("voiceFileName");

    if (!isRecording) {

        try {

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {

                const audioBlob = new Blob(audioChunks, { type: "audio/webm" });

                const formData = new FormData();
                formData.append("voice", audioBlob);

                // Send voice to Flask
                const response = await fetch("/upload_voice", {
                    method: "POST",
                    body: formData
                });

                const result = await response.json();

                // Save filename in hidden input
                voiceInput.value = result.file_name;

                // Preview audio
                const audioURL = URL.createObjectURL(audioBlob);
                const audio = document.createElement("audio");
                audio.controls = true;
                audio.src = audioURL;

                status.innerHTML = "Voice Saved:";
                status.appendChild(audio);

                audioChunks = [];
            };

            mediaRecorder.start();
            isRecording = true;

            status.innerHTML = "🎤 Recording... Click button again to stop";

        } catch (error) {

            console.error(error);
            status.innerHTML = "Microphone access denied.";

        }

    } else {

        mediaRecorder.stop();
        isRecording = false;

        status.innerHTML = "Recording stopped... processing";

    }
}


function toggleDetails(id){

let x = document.getElementById(id);

if(x.style.display === "none" || x.style.display === ""){
x.style.display = "block";
}
else{
x.style.display = "none";
}
}

/*feedback*/
// ⭐ STAR CLICK FUNCTION
const stars = document.querySelectorAll(".star");
const ratingValue = document.getElementById("rating-value");

stars.forEach(star => {
  star.addEventListener("click", () => {
    let value = star.getAttribute("data-value");
    ratingValue.value = value;

    stars.forEach(s => {
      s.style.color = "#ccc";
    });

    for (let i = 0; i < value; i++) {
      stars[i].style.color = "orange";
    }
  });
});


// ✅ FORM VALIDATION
function validateForm() {
  let category = document.getElementById("category").value;
  let message = document.getElementById("message").value.trim();
  let rating = document.getElementById("rating-value").value;

  if (category === "" || message === "" || rating === "") {
    alert("Please fill all required fields including rating!");
    return false;
  }

  return true;
}


/*sos */
function sendSOS() {
  navigator.geolocation.getCurrentPosition(
    function(position) {

      const lat = position.coords.latitude;
      const lng = position.coords.longitude;

      fetch("/send_sos", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          lat: lat,
          lng: lng
        })
      })
      .then(res => res.json())
      .then(data => alert(data.status));

    },
    function(error) {
      alert("Please allow location to send SOS 🚨");
    },
    {
      enableHighAccuracy: true
    }
  );
}

/*admin feedback pop up*/

function showToast(message, type="success") {
    const toast = document.createElement("div");
    toast.className = "toast " + type;
    toast.innerText = message;

    document.getElementById("toast-container").appendChild(toast);

    setTimeout(() => {
        toast.classList.add("show");
    }, 100);

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Trigger flash messages
if (typeof messages !== "undefined" && messages.length > 0) {
    messages.forEach(msg => {
        showToast(msg[1], msg[0]);
    });
}