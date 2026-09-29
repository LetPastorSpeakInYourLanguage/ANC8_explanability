import HelpTopic from "@/components/help/HelpTopic";
import { TOPIC_KEYS } from "@/lib/help/topics";

// One page per Help topic, generated at build time so the static export has them all.
export const dynamicParams = false;

export function generateStaticParams() {
  return TOPIC_KEYS.map((topic) => ({ topic }));
}

export default async function Page({ params }: { params: Promise<{ topic: string }> }) {
  const { topic } = await params;
  return <HelpTopic topicKey={topic} />;
}
