$(document).ready(function() {
    // Example: Confirmation for delete actions
    $('.delete-btn').on('click', function(e) {
        if (!confirm('Are you sure you want to delete this item?')) {
            e.preventDefault();
        }
    });

    // Example: Live update for public results (if implemented via AJAX polling)
    // This is a placeholder and would require backend changes to serve live data
    if ($('#public-result-container').length) {
        setInterval(function() {
            // $.ajax({
            //     url: '/api/live_public_results', // An API endpoint that serves live results
            //     success: function(data) {
            //         // Update the #public-result-container with new data
            //         console.log("Live results updated:", data);
            //     }
            // });
        }, 30000); // Poll every 30 seconds
    }

    // Handle quiz submission (example for take_quiz page)
    $('#quiz-form').on('submit', function(e) {
        e.preventDefault();
        var quizAttemptId = $(this).data('quiz-attempt-id');
        var answers = {};
        $('input[type="radio"]:checked').each(function() {
            var questionId = $(this).attr('name').replace('question_', '');
            answers[questionId] = $(this).val();
        });

        $.ajax({
            url: `/submit_quiz_answers/${quizAttemptId}`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ answers: answers }),
            success: function(response) {
                if (response.status === 'success') {
                    alert('Quiz submitted! Your score: ' + response.score);
                    window.location.href = response.redirect_url;
                } else {
                    alert('Error submitting quiz: ' + response.message);
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
                alert('An error occurred during submission.');
                console.error("AJAX error:", textStatus, errorThrown, jqXHR.responseText);
            }
        });
    });

    // Initialize select2 for multi-select (e.g., in schedule_quiz, stages_quiz forms)
    // You would need to include the Select2 library for this to work
    // $('#contestants').select2();
    // $('#questions').select2();
});
