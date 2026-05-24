document.addEventListener('DOMContentLoaded', function() {
    const filterLinks = document.querySelectorAll('.item-link');
    const projectImages = document.querySelectorAll('.project-img');

    filterLinks.forEach(link => {
        link.addEventListener('click', function() {
            const filterValue = this.getAttribute('data-filter');

            // Remove active class from all links
            filterLinks.forEach(item => item.classList.remove('menu-active'));
            // Add active class to the clicked link
            this.classList.add('menu-active');

            projectImages.forEach(image => {
                const imageType = image.getAttribute('data-type');
                if (filterValue === 'all' || imageType === filterValue) {
                    image.style.display = 'block'; // Show image
                } else {
                    image.style.display = 'none'; // Hide image
                }
            });
        });
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const galleryContainer = document.getElementById("gallery-container");
    const filterButtons = document.querySelectorAll(".item-link");

    function fetchGallery(category) {
        fetch(`/gallery/fetch/${category}/`)
            .then(response => response.json())
            .then(data => {
                galleryContainer.innerHTML = ""; // Clear existing images
                
                if (data.gallery.length === 0) {
                    galleryContainer.innerHTML = "<p>No images available.</p>";
                    return;
                }

                data.gallery.forEach(item => {
                    const galleryItem = `
                        <div class="project-img" data-type="${item.category}">
                            <img src="${item.image_url}" alt="${item.title}">
                            <div class="overlay">
                                <p>${item.description}</p>
                            </div>
                        </div>
                    `;
                    galleryContainer.innerHTML += galleryItem;
                });
            })
            .catch(error => console.error("Error fetching gallery:", error));
    }

    // Add event listener to each filter button
    filterButtons.forEach(button => {
        button.addEventListener("click", function () {
            let category = this.getAttribute("data-filter");
            
            // Remove active class from all buttons
            filterButtons.forEach(btn => btn.classList.remove("menu-active"));
            
            // Add active class to the clicked button
            this.classList.add("menu-active");

            // Fetch new gallery items
            fetchGallery(category);
        });
    });

    // Fetch all images initially
    fetchGallery("all");
});
