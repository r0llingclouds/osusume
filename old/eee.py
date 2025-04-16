crew = Crew(
    agents=[mapper],
    tasks=[map_request],
    process=Process.sequential,
)
crew.kickoff(inputs={"user_request": prompt})



