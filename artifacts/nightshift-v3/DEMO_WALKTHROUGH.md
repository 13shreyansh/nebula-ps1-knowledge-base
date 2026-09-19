# NightShift operator demo

Start at the deployed URL. The initial view explicitly labels the accepted public reference for scenario A. A fresh calculation is available through New plan; it is not implied by loading the reference.

1. Show the network and move the week slider. Work cards and network highlights use the actual schedule.
2. Open Work schedule. Search A001 and open the activity to inspect its access visits.
3. Open Delivery insights to see workload and actual schedule-derived contract completion.
4. Start live voice. Allow microphone access. Ask: “Explain this plan in simple terms.”
5. Say or type: “Platform BET S15 eastbound is unavailable in week 21. Set its capacity to zero for that week.”
6. Review the proposed restriction and calculate recovery. The operator explicitly chooses whether to adopt it.
7. Expand changed activities. On the tested public A baseline, a real run changed A001, A017, A040 and A057, preserved all visits before week 21, and retained objective zero. Exact choices can vary by run.
8. Adopt recovery. The network, schedule, metrics and analytics update to the candidate. The restriction remains visible. Export downloads the three output CSVs in a ZIP.

Alternative: New plan → Use public dataset → choose A/B/C → Calculate new plan, or upload a different eight-file input ZIP. This runs CP-SAT and validates the new output.

## Verified boundaries

- Voice is GPT-Live-1 via the official Live WebRTC API. Backend queries use Responses with gpt-5.6-terra.
- API key stays on the server, outside the frontend and source archive.
- Changes currently support location capacity restrictions for a week range, including capacity zero. The source dataset has no fleet-level train failure records; the assistant must clarify the affected location and weeks.
- Earlier access visits are frozen. A recovery is independently scored and feasibility checked before review.
- Zero is the lower bound of the primary penalty objective. Minimum activity changes are not proven.
- An accepted reference is identified explicitly. Newly computed recovery is locally validated and is not a new organizer-portal submission.
- The active plan is persisted in this browser. It is not a shared multi-user dispatch database.
- This is a working planning demonstration, not an integration with live railway control equipment.
