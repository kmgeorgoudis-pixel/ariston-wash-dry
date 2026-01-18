// ------- DATA: QUESTIONS & ANSWERS -------
const faqData = [
  { id: 1, question: "How does the washing machine work?", answer: "Select a program, detergent, and softener, insert coins, load your clothes, and wait for the cycle to finish." },
  { id: 2, question: "What should I do before putting clothes in the machine?", answer: "Check pockets for items, separate whites from colors, and follow the care labels on your garments." },
  { id: 3, question: "How long does a washing cycle take?", answer: "A full washing cycle takes approximately 20-30 minutes." },
  { id: 4, question: "How long does drying take?", answer: "Drying occurs in 15-minute cycles." },
  { id: 5, question: "Do I need to bring my own detergent and softener?", answer: "No, our machines have an automatic dosing system for detergent and softener." },
  { id: 6, question: "How much does a wash cost?", answer: "Prices are displayed in-store and on our pricing page: https://aristonwashdry.gr/timokatalogos" },
  { id: 7, question: "How much does drying cost?", answer: "Costs depend on the program and duration. More info here: https://aristonwashdry.gr/timokatalogos" },
  { id: 8, question: "Can I use my own detergent?", answer: "Not necessary, our machines have an automatic dosing system, but you can ask staff if needed." },
  { id: 9, question: "Do you accept cash or only card?", answer: "We accept both cash and card for your convenience." },
  { id: 10, question: "Do I need to stay while the laundry is running?", answer: "It is recommended to stay until the cycle is complete for safety and quick collection." },
  { id: 11, question: "Can I wash blankets?", answer: "Yes, you can wash blankets in the larger machines suitable for heavy loads." },
  { id: 12, question: "Can I wash duvets?", answer: "Yes, large machines are ideal for duvets and bulky items." },
  { id: 13, question: "Can I wash rugs?", answer: "No, our machines are not designed for rugs." },
  { id: 14, question: "Can I wash heavily stained clothes?", answer: "Yes, but pre-treatment at home is recommended for tough stains." },
  { id: 15, question: "Can I dry wool clothes?", answer: "Not recommended, as they may shrink or get damaged." },
  { id: 16, question: "Can I dry blankets and duvets?", answer: "Yes, our dryers are suitable, but always choose the correct program." },
  { id: 17, question: "Can I wash clothes with zippers and buttons?", answer: "Yes, but close zippers and fasten buttons to prevent damage." },
  { id: 18, question: "Can I wash clothes with metal parts?", answer: "Yes, but be careful with delicate fabrics." },
  { id: 19, question: "Is there a program for delicate clothes?", answer: "Yes, select the suitable program according to the machine's indications." },
  { id: 20, question: "Can I dry sports clothes?", answer: "Yes, lower temperatures are recommended to protect the fabric." },
  { id: 21, question: "What are the store hours?", answer: "Open daily from 07:00–23:00. More info: https://aristonwashdry.gr/epikoinonia" },
  { id: 22, question: "Are you open on Sundays and holidays?", answer: "Yes, except for special announcements on the website." },
  { id: 23, question: "Can I come late at night?", answer: "Yes, within operating hours." },
  { id: 24, question: "Is there staff on-site?", answer: "Yes, staff is present at specific hours." },
  { id: 25, question: "Is there security cameras?", answer: "Yes, the area is monitored for safety." },
  { id: 26, question: "How can I pay?", answer: "You can pay by card or cash, as preferred." },
  { id: 27, question: "Do you accept e-wallets?", answer: "Yes, if your card supports Revolut, Apple Pay, or Google Pay." },
  { id: 28, question: "Are there discounts or offers?", answer: "Yes, promotional offers are available from time to time." },
  { id: 29, question: "How can I use a coupon?", answer: "You can use a coupon when staff is available." },
  { id: 30, question: "Where can I find available coupons?", answer: "On our website and at the store." },
  { id: 31, question: "The washing machine doesn't start. What should I do?", answer: "Check door, program, and payment." },
  { id: 32, question: "My card is declined.", answer: "Try contactless payment or another card." },
  { id: 33, question: "The machine has no water.", answer: "Wait a bit, water starts after cycle begins." },
  { id: 34, question: "The dryer is not heating.", answer: "Check temperature and duration." },
  { id: 35, question: "The machine stopped.", answer: "Check the display for completion messages." },
  { id: 36, question: "Where is the store located?", answer: "Dervenakion 10, Vathy, Samos 83100." },
  { id: 37, question: "Is there parking?", answer: "Yes, usually nearby." },
  { id: 38, question: "Is there wheelchair access?", answer: "Yes, fully accessible." },
  { id: 39, question: "Is there Wi-Fi?", answer: "Yes, free Wi-Fi is provided." },
  { id: 40, question: "Is there a waiting area?", answer: "Yes, with comfortable seating." },
  { id: 41, question: "Do I need coins?", answer: "We accept both card and cash." },
  { id: 42, question: "Can I leave clothes and leave?", answer: "Yes, at your own risk." },
  { id: 43, question: "Can I use two machines?", answer: "Yes, if available." },
  { id: 44, question: "Can I wash and dry in the same visit?", answer: "Yes, first wash then dry." },
  { id: 45, question: "Machine capacity for washing?", answer: "Small 10kg, large 14kg." },
  { id: 46, question: "Machine capacity for drying?", answer: "Small 14kg, large 18kg." },
  { id: 47, question: "Do I need to clean the filter?", answer: "After some washes, machines clean automatically. You can also clean before washing for €0.50." },
  { id: 48, question: "Do clothes smell nice after washing?", answer: "Yes, we use quality softener." },
  { id: 49, question: "Do clothes come almost dry?", answer: "Yes, they come well drained; you can use the dryer for complete dryness." },
  { id: 50, question: "Where are instructions?", answer: "On the machines and on the store screen." },
  { id: 51, question: "Other questions?", answer: "For any additional questions, call +30 698 759 8416, 694 461 5574 or 694 889 7391. You can also email aristonwashing@gmail.com or fill the contact form on our website: https://aristonwashdry.gr/epikoinonia." }
];

document.addEventListener("DOMContentLoaded", function () {

    const greetingEl = document.getElementById("ai-greeting");
    const fullName = greetingEl.dataset.fullname;
    const avatarPath = greetingEl.dataset.avatar;

    greetingEl.textContent =
        `Hello, ${fullName}! I am the ARISTON AI Assistant. Please select a question from the left.`;

    const faqQuestionsContainer = document.getElementById("ariston-chat-questions");
    const faqMessagesContainer = document.getElementById("ariston-chat-messages");

    function renderQuestions(list) {
        faqQuestionsContainer.innerHTML = "";

        list.forEach(item => {
            const div = document.createElement("div");
            div.className = "question-item";
            div.dataset.id = item.id;
            div.textContent = item.question;

            div.addEventListener("click", () => {
                document.querySelectorAll(".question-item").forEach(x => x.classList.remove("active"));
                div.classList.add("active");

                faqMessagesContainer.innerHTML += `
                    <div class="user-msg">
                        <div class="bubble">${item.question}</div>
                    </div>
                `;

                faqMessagesContainer.innerHTML += `
                    <div class="ai-msg">
                        <img class="ai-avatar" src="${avatarPath}">
                        <div class="bubble">${item.answer}</div>
                    </div>
                `;  

                faqMessagesContainer.scrollTop = faqMessagesContainer.scrollHeight;
            });

            faqQuestionsContainer.appendChild(div);
        });
    }

    renderQuestions(faqData);

});
