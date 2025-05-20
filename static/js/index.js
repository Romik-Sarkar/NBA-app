//index script

document.addEventListener('DOMContentLoaded', function() {
    // Initialize
    const dateInput = document.getElementById('date');
    const teamSelect = document.getElementById('team');
    const applyButton = document.getElementById('apply-filters');
    const gamesGrid = document.querySelector('.games-grid');
    const gamesCounter = document.querySelector('.games-counter');
    const displayedDate = document.getElementById('displayed-date');
    
    // Format date for display
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
    
    // Fetch teams for the dropdown
    function fetchTeams() {
        fetch('/api/teams')
            .then(response => response.json())
            .then(nbaTeams => {
                // Fix: Changed from team-dropdown to team
                const dropdown = document.getElementById('team');
                nbaTeams.forEach(team => {
                    const option = document.createElement('option');
                    option.value = team.abbreviation;
                    option.textContent = team.full_name;
                    dropdown.appendChild(option);
                });
            })
            .catch(error => console.error('Error fetching teams:', error));
    }
    
    // Function to load team logos using an external API
    function loadTeamLogos() {
        // We should call this after game cards are added to the DOM
        setTimeout(() => {
            document.querySelectorAll('.team-logo').forEach(logo => {
                const teamAbbr = logo.dataset.abbr?.toLowerCase();
                
                if (!teamAbbr) return;
                
                const img = document.createElement('img');
                // Fix: Use a more reliable NBA logo source
                img.src = `https://cdn.nba.com/logos/nba/${teamAbbr}/global/L/logo.svg`;
                // Fallback to ESPN if the NBA CDN doesn't work
                img.onerror = () => {
                    img.src = `https://a.espncdn.com/i/teamlogos/nba/500/${teamAbbr}.png`;
                    
                    // If ESPN also fails, use text abbreviation
                    img.onerror = () => {
                        img.remove();
                        logo.textContent = teamAbbr.toUpperCase();
                    };
                };
                
                img.alt = `${teamAbbr.toUpperCase()} logo`;
                
                // Clear the logo container and add the image
                logo.textContent = '';
                logo.appendChild(img);
            });
        }, 500); // Small delay to ensure DOM is updated
    }

    // Create a game card
    function createGameCard(game) {
        const gameCard = document.createElement('div');
        gameCard.className = 'game-card';
        gameCard.dataset.gameId = game.game_id;
        gameCard.dataset.homeTeamId = game.home_team.id;
        gameCard.dataset.visitorTeamId = game.visitor_team.id;
        
        let scoreDisplay = '';
        
        // Show score if game is in progress or final
        if (game.status.id > 1 && game.visitor_team.score !== null && game.home_team.score !== null) {
            scoreDisplay = `
                <div class="team-score">${game.visitor_team.score}</div>
                <div class="team-score">${game.home_team.score}</div>
            `;
        } else {
            // For upcoming games, show a "VS" indicator instead of scores
            scoreDisplay = `<div class="vs-indicator">VS</div>`;
        }
        
        // Display game status (in progress, final) or game time (if not started)
        let statusDisplay = game.status.id > 1 ? game.status.text : game.game_time;
        
        gameCard.innerHTML = `
            <div class="game-status">${statusDisplay}</div>
            <div class="teams-container">
                <div class="team visitor">
                    <div class="team-logo" data-abbr="${game.visitor_team.abbreviation}"></div>
                    <div class="team-name">${game.visitor_team.name}</div>
                </div>
                ${scoreDisplay}
                <div class="team home">
                    <div class="team-logo" data-abbr="${game.home_team.abbreviation}"></div>
                    <div class="team-name">${game.home_team.name}</div>
                </div>
            </div>
        `;
        
        return gameCard;
    }

    // Fetch games for a specific date
    function fetchGames(date) {
        gamesGrid.innerHTML = '<div class="loading">Loading games...</div>';
        
        const apiDate = formatApiDate(date);
        
        fetch(`/api/games?date=${apiDate}`)
            .then(response => response.json())
            .then(data => {
                gamesGrid.innerHTML = '';
                displayedDate.textContent = formatDisplayDate(date);
                
                if (data.games.length === 0) {
                    gamesGrid.innerHTML = '<div class="no-games">No games scheduled for this date.</div>';
                    gamesCounter.textContent = '0 games';
                    return;
                }
                
                // Update games counter
                gamesCounter.textContent = `${data.games.length} game${data.games.length !== 1 ? 's' : ''}`;
                
                // Create and append game cards
                data.games.forEach(game => {
                    const gameCard = createGameCard(game);
                    gamesGrid.appendChild(gameCard);
                });
                
                // Call loadTeamLogos after adding game cards to DOM
                loadTeamLogos();
                
                applyFilters();
            })
            .catch(error => {
                console.error('Error fetching games:', error);
                gamesGrid.innerHTML = '<div class="error">Failed to load games. Please try again later.</div>';
                gamesCounter.textContent = '0 games';
            });
    }
    
    // Apply filters to the games
    function applyFilters() {
        const selectedTeam = teamSelect.value;
        const confidenceLevel = document.getElementById('confidence').value;
        
        let visibleGames = 0;
        const gameCards = document.querySelectorAll('.game-card');
        
        gameCards.forEach(card => {
            // Team filter
            const homeTeamId = card.dataset.homeTeamId;
            const visitorTeamId = card.dataset.visitorTeamId;
            const showByTeam = selectedTeam === 'all' || 
                              selectedTeam === homeTeamId || 
                              selectedTeam === visitorTeamId;
            
            // Confidence filter would be implemented with actual prediction data
            // For now, we'll just show all games that match the team filter
            const showByConfidence = true;
            
            if (showByTeam && showByConfidence) {
                card.style.display = '';
                visibleGames++;
            } else {
                card.style.display = 'none';
            }
        });
        
        // Update counter
        gamesCounter.textContent = `${visibleGames} game${visibleGames !== 1 ? 's' : ''}`;
        
        // Show message if no games match filters
        if (visibleGames === 0 && document.querySelectorAll('.game-card').length > 0) {
            const noMatchesEl = document.querySelector('.no-matches') || document.createElement('div');
            noMatchesEl.className = 'no-matches';
            noMatchesEl.textContent = 'No games match your filters.';
            
            if (!document.querySelector('.no-matches')) {
                gamesGrid.appendChild(noMatchesEl);
            }
        } else {
            const noMatchesEl = document.querySelector('.no-matches');
            if (noMatchesEl) {
                noMatchesEl.remove();
            }
        }
    }
    
    // Event listeners
    applyButton.addEventListener('click', function() {
        fetchGames(dateInput.value);
    });
    
    dateInput.addEventListener('change', function() {
        fetchGames(this.value);
    });
    

    fetchTeams();
    fetchGames(dateInput.value);
});