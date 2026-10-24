use accesskit::Role;
use bevy_a11y::AccessibilityNode;
use bevy_app::{App, Plugin};
use bevy_ecs::query::Has;
use bevy_ecs::{
    component::Component,
    entity::Entity,
    observer::On,
    query::With,
    reflect::ReflectComponent,
    system::{Commands, Query},
};
use bevy_input::keyboard::{KeyCode, KeyboardInput};
use bevy_input::ButtonState;
use bevy_input_focus::{Focusable, FocusedInput};
use bevy_picking::events::{
    PointerCancel, PointerClick, PointerDragEnd, PointerPress, PointerRelease,
};
use bevy_reflect::Reflect;
use bevy_ui::{InteractionDisabled, Pressed};

use crate::Activate;

/// Headless button widget. This widget maintains a "pressed" state, which is used to
/// indicate whether the button is currently being pressed by the user. It emits an [`Activate`]
/// event when the button is un-pressed.
#[derive(Component, Default, Debug, Clone)]
#[require(AccessibilityNode(accesskit::Node::new(Role::Button)), Focusable)]
#[derive(Reflect)]
#[reflect(Component)]
pub struct Button;

/// Optional marker component that indicates we want the button to activate on the pointer down
/// event, this is used for menu buttons.
#[derive(Component, Default, Debug, Clone, Reflect)]
#[reflect(Component)]
pub struct ActivateOnPress;

fn button_on_key_event(
    mut event: On<FocusedInput<KeyboardInput>>,
    q_state: Query<Has<InteractionDisabled>, With<Button>>,
    mut commands: Commands,
) {
    if let Ok(disabled) = q_state.get(event.focused_entity)
        && !disabled
    {
        let input_event = &event.input;
        if !input_event.repeat
            && input_event.state == ButtonState::Pressed
            && (input_event.key_code == KeyCode::Enter
                || input_event.key_code == KeyCode::NumpadEnter
                || input_event.key_code == KeyCode::Space)
        {
            event.propagate(false);
            commands.trigger(Activate {
                entity: event.focused_entity,
            });
        }
    }
}

fn button_on_pointer_click(
    mut click: On<PointerClick>,
    mut q_state: Query<
        (Has<Pressed>, Has<InteractionDisabled>, Has<ActivateOnPress>),
        With<Button>,
    >,
    mut commands: Commands,
) {
    if let Ok((pressed, disabled, activate_on_press)) = q_state.get_mut(click.entity) {
        click.propagate(false);
        if pressed && !disabled && !activate_on_press {
            commands.trigger(Activate {
                entity: click.entity,
            });
        }
    }
}

fn button_on_pointer_down(
    mut press: On<PointerPress>,
    mut q_state: Query<
        (
            Entity,
            Has<InteractionDisabled>,
            Has<Pressed>,
            Has<ActivateOnPress>,
        ),
        With<Button>,
    >,
    mut commands: Commands,
) {
    if let Ok((button, disabled, pressed, activate_on_press)) = q_state.get_mut(press.entity) {
        press.propagate(false);
        if !disabled && !pressed {
            commands.entity(button).insert(Pressed);
            if activate_on_press {
                commands.trigger(Activate { entity: button });
            }
        }
    }
}

fn button_on_pointer_up(
    mut release: On<PointerRelease>,
    mut q_state: Query<(Entity, Has<Pressed>), With<Button>>,
    mut commands: Commands,
) {
    if let Ok((button, pressed)) = q_state.get_mut(release.entity) {
        release.propagate(false);
        if pressed {
            commands.entity(button).remove::<Pressed>();
        }
    }
}

fn button_on_pointer_drag_end(
    mut drag_end: On<PointerDragEnd>,
    mut q_state: Query<(Entity, Has<Pressed>), With<Button>>,
    mut commands: Commands,
) {
    if let Ok((button, pressed)) = q_state.get_mut(drag_end.entity) {
        drag_end.propagate(false);
        if pressed {
            commands.entity(button).remove::<Pressed>();
        }
    }
}

fn button_on_pointer_cancel(
    mut cancel: On<PointerCancel>,
    mut q_state: Query<(Entity, Has<Pressed>), With<Button>>,
    mut commands: Commands,
) {
    if let Ok((button, pressed)) = q_state.get_mut(cancel.entity) {
        cancel.propagate(false);
        if pressed {
            commands.entity(button).remove::<Pressed>();
        }
    }
}

/// Plugin that adds the observers for the [`Button`] widget.
pub struct ButtonPlugin;

impl Plugin for ButtonPlugin {
    fn build(&self, app: &mut App) {
        app.add_observer(button_on_key_event)
            .add_observer(button_on_pointer_down)
            .add_observer(button_on_pointer_up)
            .add_observer(button_on_pointer_click)
            .add_observer(button_on_pointer_drag_end)
            .add_observer(button_on_pointer_cancel);
    }
}

#[cfg(test)]
mod tests {
    use super::{Activate, ActivateOnPress, Button, ButtonPlugin};
    use bevy_app::App;
    use bevy_camera::NormalizedRenderTarget;
    use bevy_ecs::{entity::Entity, observer::On, resource::Resource, system::ResMut};
    use bevy_math::Vec2;
    use bevy_picking::{
        backend::HitData,
        events::{
            Pointer, PointerCancel, PointerClick, PointerDragEnd, PointerPress, PointerRelease,
        },
        pointer::{Location, PointerButton, PointerId},
    };
    use bevy_ui::{InteractionDisabled, Pressed};
    use bevy_window::WindowRef;
    use core::time::Duration;

    #[derive(Resource, Default)]
    struct Activations(u32);

    #[derive(Clone, Copy)]
    enum Cleanup {
        Release,
        DragEnd,
        Cancel,
    }

    fn setup() -> (App, Entity, Pointer, HitData) {
        let mut app = App::new();
        app.add_plugins(ButtonPlugin).init_resource::<Activations>();
        app.add_observer(|_: On<Activate>, mut count: ResMut<Activations>| count.0 += 1);
        app.world_mut().flush();
        let window = app.world_mut().spawn_empty().id();
        let button = app.world_mut().spawn(Button).id();
        let pointer = Pointer::new(
            PointerId::Mouse,
            Location {
                target: NormalizedRenderTarget::Window(
                    WindowRef::Entity(window).normalize(None).unwrap(),
                ),
                position: Vec2::ZERO,
            },
        );
        let hit = HitData::new(window, 0.0, None, None);
        (app, button, pointer, hit)
    }

    fn press(app: &mut App, button: Entity, pointer: &Pointer, hit: &HitData) {
        app.world_mut().trigger(PointerPress {
            entity: button,
            pointer: pointer.clone(),
            button: PointerButton::Primary,
            hit: hit.clone(),
            count: 1,
        });
        app.world_mut().flush();
    }

    fn cleanup_clears_pressed(cleanup: Cleanup, disabled: bool) {
        let (mut app, button, pointer, hit) = setup();
        press(&mut app, button, &pointer, &hit);
        assert!(app.world().entity(button).contains::<Pressed>());
        if disabled {
            app.world_mut()
                .entity_mut(button)
                .insert(InteractionDisabled);
        }
        match cleanup {
            Cleanup::Release => app.world_mut().trigger(PointerRelease {
                entity: button,
                pointer,
                button: PointerButton::Primary,
                hit,
            }),
            Cleanup::DragEnd => app.world_mut().trigger(PointerDragEnd {
                entity: button,
                pointer,
                button: PointerButton::Primary,
                distance: Vec2::ONE,
            }),
            Cleanup::Cancel => app.world_mut().trigger(PointerCancel {
                entity: button,
                pointer,
                hit,
            }),
        }
        app.world_mut().flush();
        assert!(!app.world().entity(button).contains::<Pressed>());
        assert_eq!(app.world().resource::<Activations>().0, 0);
        app.world_mut()
            .entity_mut(button)
            .remove::<InteractionDisabled>();
        assert!(!app.world().entity(button).contains::<Pressed>());
    }

    #[test]
    fn release_cleans_up_a_button_disabled_during_press() {
        cleanup_clears_pressed(Cleanup::Release, true);
    }

    #[test]
    fn drag_end_cleans_up_a_button_disabled_during_press() {
        cleanup_clears_pressed(Cleanup::DragEnd, true);
    }

    #[test]
    fn cancel_cleans_up_a_button_disabled_during_press() {
        cleanup_clears_pressed(Cleanup::Cancel, true);
    }

    #[test]
    fn enabled_buttons_still_clear_on_every_pointer_cleanup() {
        for cleanup in [Cleanup::Release, Cleanup::DragEnd, Cleanup::Cancel] {
            cleanup_clears_pressed(cleanup, false);
        }
    }

    #[test]
    fn disabled_clicks_do_not_activate_but_enabled_clicks_do() {
        for disabled in [false, true] {
            let (mut app, button, pointer, hit) = setup();
            press(&mut app, button, &pointer, &hit);
            if disabled {
                app.world_mut()
                    .entity_mut(button)
                    .insert(InteractionDisabled);
            }
            app.world_mut().trigger(PointerClick {
                entity: button,
                pointer,
                hit,
                button: PointerButton::Primary,
                duration: Duration::from_millis(50),
                count: 1,
            });
            app.world_mut().flush();
            assert_eq!(
                app.world().resource::<Activations>().0,
                u32::from(!disabled)
            );
        }
    }

    #[test]
    fn activate_on_press_stays_blocked_when_disabled() {
        for disabled in [false, true] {
            let (mut app, button, pointer, hit) = setup();
            app.world_mut().entity_mut(button).insert(ActivateOnPress);
            if disabled {
                app.world_mut()
                    .entity_mut(button)
                    .insert(InteractionDisabled);
            }
            press(&mut app, button, &pointer, &hit);
            assert_eq!(app.world().entity(button).contains::<Pressed>(), !disabled);
            assert_eq!(
                app.world().resource::<Activations>().0,
                u32::from(!disabled)
            );
        }
    }
}
