//! The counter transition, shared by pointer input and remote commands.
//! It has no engine dependencies so CI can test it without a renderer.

pub const COUNT_LIMIT: u32 = 10;

#[derive(Default, Debug, PartialEq, Eq)]
pub struct Counter {
    revision: u64,
    count: u32,
}

impl Counter {
    pub fn revision(&self) -> u64 {
        self.revision
    }

    pub fn count(&self) -> u32 {
        self.count
    }

    pub fn increment(&mut self) -> Result<(), &'static str> {
        if self.count >= COUNT_LIMIT {
            return Err("The counter has reached its limit.");
        }
        self.count += 1;
        self.revision += 1;
        Ok(())
    }

    pub fn act(&mut self, action: &str, expected_revision: u64) -> Result<(), &'static str> {
        if action != "increment" {
            return Err("Unknown action.");
        }
        if expected_revision != self.revision {
            return Err("The state revision has changed. Read agent.state again.");
        }
        self.increment()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepted_command_advances_once() {
        let mut counter = Counter::default();
        assert_eq!((counter.count(), counter.revision()), (0, 0));
        counter.act("increment", 0).unwrap();
        assert_eq!((counter.count(), counter.revision()), (1, 1));
    }

    #[test]
    fn rejected_commands_preserve_state() {
        let mut counter = Counter::default();
        counter.act("increment", 0).unwrap();
        assert!(counter.act("increment", 0).is_err());
        assert!(counter.act("unknown", 1).is_err());
        assert_eq!((counter.count(), counter.revision()), (1, 1));
    }

    #[test]
    fn pointer_and_command_transitions_match() {
        let mut pointer = Counter::default();
        let mut remote = Counter::default();
        for revision in 0..u64::from(COUNT_LIMIT) {
            pointer.increment().unwrap();
            remote.act("increment", revision).unwrap();
            assert_eq!(pointer, remote);
        }
        assert!(pointer.increment().is_err());
        assert!(remote.act("increment", u64::from(COUNT_LIMIT)).is_err());
        assert_eq!(pointer, remote);
        assert_eq!((pointer.count(), pointer.revision()), (COUNT_LIMIT, 10));
    }
}
