# Contributing

Feature branch -> meaningful tests -> PR -> review -> merge. Use docs/GIT_GITHUB_WALKTHROUGH_KO.md.
Keep pure modules independent of ROS; MAVROS belongs only in alatus_mavros.
No shadow launch may start a command publisher. A passing mock test is not flight acceptance.
Do not commit weights, secrets, videos or flight logs. Include environment and exact command/evidence in PR.
