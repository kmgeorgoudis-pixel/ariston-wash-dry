// ------- DATA: QUESTIONS & ANSWERS -------
const faqEnglish = [
  { id: 1, question: "How does the washing machine work?", answer: "Select your program,  insert the payment, load your laundry, and wait for the cycle to complete." },
  { id: 2, question: "What should I do before loading the laundry?", answer: "Check pockets for any objects, separate whites from colors, and follow the care instructions on the clothing labels." },
  { id: 3, question: "How long does a wash cycle take?", answer: "A full wash cycle takes approximately 20-30 minutes." },
  { id: 4, question: "How long does drying take?", answer: "Drying is performed in 15-minute cycles." },
  { id: 5, question: "Do I need to bring my own detergent and softener?", answer: "No, our machines feature an automatic dosing system. We exclusively use certified, mild, and hypoallergenic products, ensuring maximum protection for both your garment fibers and your skin." },
  { id: 6, question: "How much does a wash cost?", answer: "Prices are posted in-store and on our website's price list page: https://aristonwashdry.gr/timokatalogos" },
  { id: 7, question: "How much does drying cost?", answer: "The cost depends on the selected program and duration. You can find detailed information here: https://aristonwashdry.gr/timokatalogos" },
  { id: 8, question: "Can I use my own detergent?", answer: "No, as the machines have an automatic dosing system. However, if you wish, you can consult our staff when they are available." },
  { id: 9, question: "Do you accept cash or card only?", answer: "We accept both cash and card for your convenience." },
  { id: 10, question: "Do I need to be present while my clothes are washing?", answer: "It is recommended to remain on-site until the cycle is finished for security and to promptly collect your laundry." },
  { id: 11, question: "Can I wash blankets?", answer: "Yes, you can wash blankets in our larger washing machines, which are suitable for heavy loads." },
  { id: 12, question: "Can I wash duvets/comforters?", answer: "Yes, our large washing machines are ideal for duvets and bulky items." },
  { id: 13, question: "Can I wash rugs?", answer: "No, our machines are not designed for washing rugs." },
  { id: 14, question: "Can I wash clothes with heavy stains?", answer: "Yes, but for very stubborn stains, we recommend pre-treating them at home or asking our staff for assistance when available." },
  { id: 15, question: "Can I dry wool clothes?", answer: "Yes, at a low temperature and with constant supervision by opening the dryer periodically; it is easy and permitted." },
  { id: 16, question: "Can I dry blankets and duvets?", answer: "Yes, our dryers are suitable for blankets and duvets, provided you select the correct program." },
  { id: 17, question: "Can I wash clothes with zippers and buttons?", answer: "Yes, but it is best to close zippers and fasten buttons to avoid any damage." },
  { id: 18, question: "Can I wash clothes with metal elements?", answer: "Yes, but there is a possibility of wear on delicate fabrics; please load them with care." },
  { id: 19, question: "Is there a program for delicate clothes?", answer: "Yes, please select the appropriate delicates program according to the device instructions." },
  { id: 20, question: "Can I dry athletic wear?", answer: "Yes, a lower temperature is recommended to protect the fabric." },
  { id: 21, question: "What are the store's opening hours?", answer: "The store is open daily from 07:00 to 23:00. Find more details here: https://aristonwashdry.gr/epikoinonia" },
  { id: 22, question: "Are you open on Sundays and holidays?", answer: "Yes, the store operates on Sundays and holidays unless there is a special announcement on our website." },
  { id: 23, question: "Can I come late at night?", answer: "Yes, you can visit us anytime within our operating hours." },
  { id: 24, question: "Is there staff at the store?", answer: "Yes, there are specific hours when staff members are present." },
  { id: 25, question: "Is there security footage in the area?", answer: "Yes, the premises are monitored by CCTV for the safety of our customers and equipment." },
  { id: 26, question: "How can I pay?", answer: "You can pay either by card or cash, depending on what suits you best." },
  { id: 27, question: "Do you accept electronic wallets?", answer: "If your card supports Revolut, Apple Pay, or Google Pay, you can use them." },
  { id: 28, question: "Are there any discounts or offers?", answer: "Yes, we occasionally have special offers and discount programs." },
  { id: 29, question: "How can I use a coupon?", answer: "You can use a coupon when staff is present at the store." },
  { id: 30, question: "Where can I find available coupons?", answer: "On our website and within the store premises." },
  { id: 31, question: "The washing machine won't start. What should I do?", answer: "Check the door, the selected program, and the payment status." },
  { id: 32, question: "My card is being declined.", answer: "Try a contactless payment or use a different card." },
  { id: 33, question: "The washing machine has no water.", answer: "Please wait a moment; the water supply begins after the cycle starts." },
  { id: 34, question: "The dryer is not heating up.", answer: "Check the temperature setting and the duration." },
  { id: 35, question: "The machine stopped.", answer: "Check the screen for a completion message." },
  { id: 36, question: "Where is the store located?", answer: "10 Dervenakion, Vathy, Samos 83100." },
  { id: 37, question: "Is there parking?", answer: "Yes, there are usually parking spots available nearby." },
  { id: 38, question: "Is there disabled access?", answer: "The space is designed for easy and comfortable access." },
  { id: 39, question: "Is there Wi-Fi?", answer: "Yes, free Wi-Fi is provided." },
  { id: 40, question: "Is there a waiting area?", answer: "Yes, there is a comfortable waiting area with seating." },
  { id: 41, question: "Do I need to bring coins?", answer: "We accept both cards and cash." },
  { id: 42, question: "Can I leave my clothes and go?", answer: "You may, but at your own risk." },
  { id: 43, question: "Can I use two washing machines at once?", answer: "Yes, if they are available." },
  { id: 44, question: "Can I wash and dry in the same visit?", answer: "Yes, first wash and then dry." },
  { id: 45, question: "What is the capacity of the washing machines?", answer: "Small machines hold 10kg, large machines hold 15kg." },
  { id: 46, question: "What is the capacity of the dryers?", answer: "Small dryers hold 15kg, large dryers hold 18kg." },
  { id: 47, question: "Do I need to clean the filter?", answer: "No, our staff takes full responsibility for cleaning the filters. Furthermore, in our washing machines, after every wash, both the clothes and the drum are disinfected with active oxygen, and a special drum disinfection program is applied for ultimate hygiene. As for the dryers, our staff ensures the meticulous cleaning of their filters every few uses." },
  { id: 48, question: "Will my clothes come out scented?", answer: "Yes, we use high-quality fabric softener." },
  { id: 49, question: "Do the clothes come out almost dry?", answer: "From the washing machine, they come out well-spun. If you wish, you can dry them completely in our drying machines." },
  { id: 50, question: "Where can I find instructions?", answer: "On the machines and on the store's display screen." },
  { id: 51, question: "Another question!", answer: "For any additional questions, you can contact us by phone at +30 698 759 8416, 694 461 5574, or 694 889 7391. Alternatively, you can email us at info@aristonwashdry.gr or fill out the contact form on our website in the Contact section: https://aristonwashdry.gr/epikoinonia. We will be happy to assist you!" }
];

document.addEventListener("DOMContentLoaded", function () {

    const greetingEl = document.getElementById("ai-greeting");
    const fullName = greetingEl.dataset.fullname || "Guest";
    const avatarPath = greetingEl.dataset.avatar || "";

    greetingEl.textContent =
        `Hello, ${fullName}! I am the ARISTON AI Assistant. Please select a question from the left.`;

    const faqQuestionsContainer = document.getElementById("ariston-chat-questions");
    const faqMessagesContainer = document.getElementById("ariston-chat-messages");

    function renderQuestions(list) {
        if (!faqQuestionsContainer) return;
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
                    <div class="ai-msg">
                        <img class="ai-avatar" src="${avatarPath}">
                        <div class="bubble">${item.answer}</div>
                    </div>
                `;

                setTimeout(() => {
                    faqMessagesContainer.scrollTo({
                        top: faqMessagesContainer.scrollHeight,
                        behavior: 'smooth'
                    });
                }, 100); 
            });

            faqQuestionsContainer.appendChild(div);
        });
    }

    
    renderQuestions(faqEnglish); 

});