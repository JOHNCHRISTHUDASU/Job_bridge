// Initialize AOS
AOS.init();

// Typed.js Animation
new Typed("#typing", {
    strings: [
        "Find Local Jobs.",
        "Hire Better Talent.",
        "Build Your Future."
    ],
    typeSpeed: 60,
    backSpeed: 40,
    loop: true
});

// =========================
// Counter Animation
// =========================

const counters = document.querySelectorAll(".counter");

counters.forEach(counter => {

    counter.innerText = "0";

    const updateCounter = () => {

        const target = +counter.getAttribute("data-target");
        const count = +counter.innerText;

        const increment = Math.ceil(target / 100);

        if (count < target) {

            counter.innerText = count + increment;

            setTimeout(updateCounter, 20);

        } else {

            counter.innerText = target.toLocaleString();

        }

    };

    updateCounter();

});
// =========================
// FAQ Accordion
// =========================

const faqItems = document.querySelectorAll(".faq-item");

faqItems.forEach(item => {

    const btn = item.querySelector(".faq-question");

    btn.addEventListener("click", () => {

        item.classList.toggle("active");

    });

});
// =========================
// Chatbot + Messaging
// =========================

document.addEventListener("DOMContentLoaded", function () {

    const chatToggle = document.getElementById("chatToggle");
    const chatContainer = document.getElementById("chatContainer");
    const closeChat = document.getElementById("closeChat");

    const sendBtn = document.getElementById("sendBtn");
    const userMessage = document.getElementById("userMessage");
    const chatBody = document.getElementById("chatBody");

    // Open Chat
    if(chatToggle){

        chatToggle.addEventListener("click",function(){

            chatContainer.style.display="flex";

        });

    }

    // Close Chat
    if(closeChat){

        closeChat.addEventListener("click",function(){

            chatContainer.style.display="none";

        });

    }

    // Send Message
async function sendMessage() {

    const message = userMessage.value.trim();

    if (message === "") return;

    // User Message
    const userDiv = document.createElement("div");
    userDiv.className = "user-message";
    userDiv.innerHTML = message;

    chatBody.appendChild(userDiv);

    userMessage.value = "";

    chatBody.scrollTop = chatBody.scrollHeight;

    try {

        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        const botDiv = document.createElement("div");
        botDiv.className = "bot-message";
        botDiv.innerHTML = data.reply;

        chatBody.appendChild(botDiv);

        chatBody.scrollTop = chatBody.scrollHeight;

    } catch (error) {

        const botDiv = document.createElement("div");
        botDiv.className = "bot-message";
        botDiv.innerHTML = "❌ Unable to connect to Gemini AI.";

        chatBody.appendChild(botDiv);

        chatBody.scrollTop = chatBody.scrollHeight;

        console.error(error);

    }

}

// Send Button
if (sendBtn) {

    sendBtn.addEventListener("click", sendMessage);

}

// Press Enter
if (userMessage) {

    userMessage.addEventListener("keydown", function (e) {

        if (e.key === "Enter") {

            e.preventDefault();

            sendMessage();

        }

    });

}

});
// =========================
// Quick Button Responses
// =========================

const quickButtons = document.querySelectorAll(".quick-btn");

quickButtons.forEach(button => {

    button.addEventListener("click", function () {

        const text = this.innerText;

        // Show user message
        const userDiv = document.createElement("div");
        userDiv.className = "user-message";
        userDiv.innerHTML = text;

        chatBody.appendChild(userDiv);

        let reply = "";

        switch(text){

            case "Find Jobs":

                reply = "💼 You can search jobs based on Location, Category, Salary, Experience and Job Type after logging in as a Job Seeker.";

                break;

            case "Apply Job":

                reply = "📄 Login as a Job Seeker → Search Jobs → Open a Job → Click <b>Apply Now</b>.";

                break;

            case "Resume Review":

                reply = "📑 Upload your resume from your dashboard. Job_Bridge AI will analyze your resume and provide suggestions to improve it.";

                break;

            case "Employer Help":

                reply = "🏢 Login as an Employer → Complete Company Profile → Post a Job → Manage Applicants → Schedule Interviews.";

                break;

            case "FAQ":

                reply = "❓ Frequently Asked Questions:<br><br>• How to register?<br>• How to apply for jobs?<br>• How to post jobs?<br>• How to upload a resume?<br>• How to contact support?";

                break;

            default:

                reply = "Hello! How can I help you?";

        }

        setTimeout(function(){

            const botDiv = document.createElement("div");

            botDiv.className = "bot-message";

            botDiv.innerHTML = reply;

            chatBody.appendChild(botDiv);

            chatBody.scrollTop = chatBody.scrollHeight;

        },500);

    });

});



const role = document.getElementById("role");
const companyField = document.getElementById("companyField");

role.addEventListener("change", function(){

    if(this.value=="Employer"){
        companyField.style.display="block";
    }
    else{
        companyField.style.display="none";
    }

});