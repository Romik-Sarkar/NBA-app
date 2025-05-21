// Enhanced date selector component with week view
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the enhanced date selector
    initDateSelector();
    
    // Global date formatting functions
    function formatDisplayDate(dateString) {
        // Parse the input date string (YYYY-MM-DD from date input)
        const parts = dateString.split('-');
        if (parts.length !== 3) {
            return dateString; // Return as is if not in expected format
        }
        
        // Create a new date using UTC to avoid timezone issues
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]) - 1; // JS months are 0-indexed
        const day = parseInt(parts[2]);
        
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${months[month]} ${day}, ${year}`;
    }

    // Format date for API
    function formatApiDate(dateString) {
        // Parse the input date string (YYYY-MM-DD from date input)
        const parts = dateString.split('-');
        if (parts.length !== 3) {
            // Fallback to current date if format is wrong
            const today = new Date();
            return `${(today.getMonth() + 1).toString().padStart(2, '0')}/${today.getDate().toString().padStart(2, '0')}/${today.getFullYear()}`;
        }
        
        // Return in MM/DD/YYYY format without creating a Date object
        // This avoids timezone issues
        return `${parts[1]}/${parts[2]}/${parts[0]}`;
    }
    
    // Date selection and week view functionality
    function initDateSelector() {
        const dateInput = document.getElementById('date');
        const weekViewContainer = document.querySelector('.week-view-container');
        const displayedDate = document.getElementById('displayed-date');
        let currentDate = new Date();
        
        // Set initial date if input has a value
        if (dateInput.value) {
            const dateParts = dateInput.value.split('-');
            if (dateParts.length === 3) {
                currentDate = new Date(dateParts[0], dateParts[1] - 1, dateParts[2]);
            }
        } else {
            // Set today's date as default
            const today = new Date();
            dateInput.value = formatDateForInput(today);
        }
        
        // Update displayed date
        if (displayedDate) {
            displayedDate.textContent = formatDisplayDate(dateInput.value);
        }
        
        // Initialize week view
        updateWeekView(currentDate);
        
        // Listen for date input changes
        dateInput.addEventListener('change', function() {
            const selectedDate = getDateFromInput(this.value);
            updateWeekView(selectedDate);
            
            // Update displayed date
            if (displayedDate) {
                displayedDate.textContent = formatDisplayDate(this.value);
            }
            
            // Call fetchGames if it exists in the global scope
            if (typeof window.fetchGames === 'function') {
                window.fetchGames(this.value);
            }
        });
        
        // Week navigation buttons
        document.getElementById('prev-week').addEventListener('click', () => {
            navigateWeek(-7);
        });
        
        document.getElementById('next-week').addEventListener('click', () => {
            navigateWeek(7);
        });
        
        // Navigate week function
        function navigateWeek(dayOffset) {
            const currentSelectedDate = getDateFromInput(dateInput.value);
            const newDate = new Date(currentSelectedDate);
            newDate.setDate(newDate.getDate() + dayOffset);
            
            // Don't change the input value or fetch games, just update the week view
            // This allows browsing weeks without changing the selected date
            updateWeekView(currentSelectedDate, newDate);
        }
        
        // Update week view based on selected date
        function updateWeekView(selectedDate, weekCenterDate = null) {
            // Use provided week center date or default to selected date
            const weekCenter = weekCenterDate || selectedDate;
            
            // Get the week start date (Sunday)
            const weekStart = new Date(weekCenter);
            weekStart.setDate(weekCenter.getDate() - weekCenter.getDay());
            
            // Clear existing days
            const weekDaysContainer = document.querySelector('.week-days');
            if (!weekDaysContainer) return; // Safety check
            
            weekDaysContainer.innerHTML = '';
            
            // Create 7 day elements
            for (let i = 0; i < 7; i++) {
                const dayDate = new Date(weekStart);
                dayDate.setDate(weekStart.getDate() + i);
                
                const dayElement = document.createElement('div');
                dayElement.className = 'week-day';
                
                // Check if this day is the selected day
                const isSelected = isSameDay(dayDate, selectedDate);
                if (isSelected) {
                    dayElement.classList.add('selected');
                }
                
                // Check if this day is today
                const isToday = isSameDay(dayDate, new Date());
                if (isToday) {
                    dayElement.classList.add('today');
                }
                
                // Format day name and date
                const dayName = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][dayDate.getDay()];
                const dayNum = dayDate.getDate();
                
                dayElement.innerHTML = `
                    <div class="day-name">${dayName}</div>
                    <div class="day-number">${dayNum}</div>
                `;
                
                // Add click event to select this day
                dayElement.addEventListener('click', () => {
                    const formattedDate = formatDateForInput(dayDate);
                    dateInput.value = formattedDate;
                    
                    // Update the week view (mark the selected day)
                    updateWeekView(dayDate);
                    
                    // Update displayed date
                    if (displayedDate) {
                        displayedDate.textContent = formatDisplayDate(formattedDate);
                    }
                    
                    // Call fetchGames if it exists in the global scope
                    if (typeof window.fetchGames === 'function') {
                        window.fetchGames(formattedDate);
                    }
                });
                
                weekDaysContainer.appendChild(dayElement);
            }
        }
    }
    
    // Helper function to check if two dates are the same day
    function isSameDay(date1, date2) {
        return date1.getDate() === date2.getDate() && 
               date1.getMonth() === date2.getMonth() && 
               date1.getFullYear() === date2.getFullYear();
    }
    
    // Helper function to get Date object from input value
    function getDateFromInput(inputValue) {
        const parts = inputValue.split('-');
        if (parts.length === 3) {
            return new Date(parts[0], parts[1] - 1, parts[2]);
        }
        return new Date(); // Fallback to today
    }
    
    // Helper function to format date for input value (YYYY-MM-DD)
    function formatDateForInput(date) {
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    // Expose key functions to global scope for access from other scripts
    window.formatDisplayDate = formatDisplayDate;
    window.formatApiDate = formatApiDate;
});