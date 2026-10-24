//! A Bevy app that can be used as an integration test target.
//! It displays a button that must be clicked. The button is placed at a random position and
//! moves every 5 seconds.
//!
//! Run with the `bevy_remote` and `bevy_feathers` feature enabled:
//! ```bash
//! cargo run --example app_under_test --features="bevy_remote bevy_feathers"
//! ```
//! This example can be paired with the `integration_test` example, which will run an integration
//! test on this app.

use bevy::{
    feathers::{
        controls::FeathersButton, dark_theme::create_dark_theme, display::caption, theme::UiTheme,
        FeathersPlugins,
    },
    prelude::*,
    remote::{error_codes, http::RemoteHttpPlugin, BrpError, BrpResult, RemotePlugin},
    text::FontSize,
    time::common_conditions::on_timer,
    ui::UiGlobalTransform,
};
use chacha20::ChaCha8Rng;
use rand::{RngExt, SeedableRng};
use serde::Deserialize;
use serde_json::{json, Value};

fn main() {
    App::new()
        .add_plugins((DefaultPlugins, FeathersPlugins))
        // To make the app available for integration testing, we add these
        // remote plugins to expose API’s for a testing framework to call.
        .add_plugins(
            RemotePlugin::default()
                .with_method_main("agent.state", agent_state)
                .with_method_main("agent.act", agent_act),
        )
        .add_plugins(RemoteHttpPlugin::default())
        .init_resource::<AgentState>()
        .insert_resource(UiTheme(create_dark_theme()))
        .insert_resource(SeededRng(ChaCha8Rng::seed_from_u64(19878367467712)))
        .add_systems(Startup, setup)
        .add_systems(
            Update,
            (
                move_button.run_if(on_timer(std::time::Duration::from_secs(5))),
                log_button_position,
                update_counter,
            ),
        )
        .run();
}

#[derive(Resource)]
struct SeededRng(ChaCha8Rng);

/// Small demo domain, deliberately independent of remote transport and UI layout.
#[derive(Resource, Default)]
struct AgentState {
    revision: u64,
    count: u32,
}

#[derive(Component)]
struct CounterText;

const COUNT_LIMIT: u32 = 10;

fn snapshot(state: &AgentState) -> Value {
    json!({
        "schema": 1,
        "revision": state.revision,
        "count": state.count,
        "limit": COUNT_LIMIT,
        "legalActions": if state.count < COUNT_LIMIT { vec!["increment"] } else { vec![] },
    })
}

fn invalid_request(message: &str) -> BrpError {
    BrpError {
        code: error_codes::INVALID_PARAMS,
        message: message.to_owned(),
        data: None,
    }
}

fn increment(state: &mut AgentState) -> Result<(), BrpError> {
    if state.count >= COUNT_LIMIT {
        return Err(invalid_request("The counter has reached its limit."));
    }
    state.count += 1;
    state.revision += 1;
    Ok(())
}

fn agent_state(In(_params): In<Option<Value>>, world: &World) -> BrpResult {
    Ok(snapshot(world.resource::<AgentState>()))
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ActionRequest {
    action: String,
    expected_revision: u64,
}

fn agent_act(In(params): In<Option<Value>>, world: &mut World) -> BrpResult {
    let request: ActionRequest = serde_json::from_value(
        params.ok_or_else(|| invalid_request("Action parameters are required."))?,
    )
    .map_err(|error| invalid_request(&error.to_string()))?;
    if request.action != "increment" {
        return Err(invalid_request("Unknown action."));
    }
    let mut state = world.resource_mut::<AgentState>();
    if request.expected_revision != state.revision {
        return Err(invalid_request(
            "The state revision has changed. Read agent.state again.",
        ));
    }
    increment(&mut state)?;
    Ok(snapshot(&state))
}

fn on_button_click(click: On<PointerClick>, mut state: ResMut<AgentState>) {
    if click.button == PointerButton::Primary {
        if let Err(error) = increment(&mut state) {
            warn!("{}", error.message);
        } else {
            info!("Button pressed! revision={}", state.revision);
        }
    }
}

fn update_counter(state: Res<AgentState>, mut text: Single<&mut Text, With<CounterText>>) {
    if state.is_changed() {
        text.0 = format!("Count: {} / {COUNT_LIMIT}", state.count);
    }
}

fn log_button_position(
    transform: Single<&UiGlobalTransform, (With<FeathersButton>, Changed<UiGlobalTransform>)>,
) {
    info!(
        "Button at physical ({}, {})",
        transform.translation.x, transform.translation.y
    );
}

fn random_position(rng: &mut ChaCha8Rng) -> (f32, f32) {
    let left_pct = rng.random_range(0.0..=60.0);
    let top_pct = rng.random_range(0.0..=60.0);
    (left_pct, top_pct)
}

fn move_button(
    mut rng: ResMut<SeededRng>,
    mut button_query: Query<&mut Node, With<FeathersButton>>,
) {
    let (left_pct, top_pct) = random_position(&mut rng.0);
    for mut node in &mut button_query {
        node.left = percent(left_pct);
        node.top = percent(top_pct);
    }
}

fn setup(mut commands: Commands, mut rng: ResMut<SeededRng>) {
    let (left_pct, top_pct) = random_position(&mut rng.0);
    commands.spawn(Camera2d);
    commands.spawn((
        CounterText,
        Text::new("Count: 0 / 10"),
        TextFont {
            font_size: FontSize::Px(32.0),
            ..default()
        },
        Node {
            position_type: PositionType::Absolute,
            left: px(16),
            top: px(16),
            ..default()
        },
    ));
    commands.spawn_scene(bsn! {
        Node {
            width: percent(100),
            height: percent(100),
        }
        Children [
            @FeathersButton {
                @caption: bsn! { @caption("Increment") }
            }
            Node {
                width: px(150),
                height: px(65),
                border: UiRect::all(px(5)),
                left: percent(left_pct),
                top: percent(top_pct),
            }
            BorderColor::all(Color::WHITE)
            on(on_button_click)
        ]
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    fn world() -> World {
        let mut world = World::new();
        world.init_resource::<AgentState>();
        world
    }

    #[test]
    fn snapshot_is_read_only_and_lists_legal_actions() {
        let world = world();
        let before = agent_state(In(None), &world).unwrap();
        assert_eq!(before["legalActions"], json!(["increment"]));
        assert_eq!(agent_state(In(None), &world).unwrap(), before);
    }

    #[test]
    fn action_and_ui_share_the_same_transition() {
        let mut world = world();
        let remote = agent_act(
            In(Some(json!({"action":"increment","expectedRevision":0}))),
            &mut world,
        )
        .unwrap();
        let mut local = AgentState::default();
        increment(&mut local).unwrap();
        assert_eq!(remote, snapshot(&local));
    }

    #[test]
    fn stale_unknown_and_malformed_actions_do_not_change_state() {
        let mut world = world();
        agent_act(
            In(Some(json!({"action":"increment","expectedRevision":0}))),
            &mut world,
        )
        .unwrap();
        let before = agent_state(In(None), &world).unwrap();
        for params in [
            None,
            Some(json!({"action":"increment","expectedRevision":0})),
            Some(json!({"action":"reset","expectedRevision":1})),
            Some(json!({"action":"increment"})),
            Some(json!({"action":"increment","expectedRevision":1,"extra":true})),
        ] {
            assert_eq!(
                agent_act(In(params), &mut world).unwrap_err().code,
                error_codes::INVALID_PARAMS
            );
            assert_eq!(agent_state(In(None), &world).unwrap(), before);
        }
    }

    #[test]
    fn limit_is_enforced_without_mutation() {
        let mut world = world();
        for revision in 0..COUNT_LIMIT {
            agent_act(
                In(Some(
                    json!({"action":"increment","expectedRevision":revision}),
                )),
                &mut world,
            )
            .unwrap();
        }
        let before = agent_state(In(None), &world).unwrap();
        assert_eq!(before["legalActions"], json!([]));
        assert!(agent_act(
            In(Some(
                json!({"action":"increment","expectedRevision":COUNT_LIMIT})
            )),
            &mut world
        )
        .is_err());
        assert_eq!(agent_state(In(None), &world).unwrap(), before);
    }
}
