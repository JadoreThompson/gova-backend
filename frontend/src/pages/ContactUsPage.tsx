import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useState, type ChangeEvent, type FC, type FormEvent } from "react";

// A simple interface for the form data
interface ContactFormData {
  name: string;
  email: string;
  company: string;
  message: string;
}

// A simple interface for validation errors
interface FormErrors {
  name?: string;
  email?: string;
  message?: string;
}

const ContactUsPage: FC = () => {
  const [formData, setFormData] = useState<ContactFormData>({
    name: "",
    email: "",
    company: "",
    message: "",
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // A single handler for all input changes
  const handleChange = (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear the error for a field when the user starts typing in it
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  // Basic validation function
  const validateForm = (): FormErrors => {
    const newErrors: FormErrors = {};
    if (!formData.name.trim()) {
      newErrors.name = "Name is required.";
    }
    if (!formData.email.trim()) {
      newErrors.email = "Email is required.";
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = "Email address is invalid.";
    }
    if (!formData.message.trim() || formData.message.trim().length < 10) {
      newErrors.message = "Message must be at least 10 characters long.";
    }
    return newErrors;
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSubmitting(true);
    // Simulate an API call
    console.log("Submitting form data:", formData);
    setTimeout(() => {
      alert("Thank you for your message! We will get back to you shortly.");
      // Reset form state
      setFormData({ name: "", email: "", company: "", message: "" });
      setErrors({});
      setIsSubmitting(false);
    }, 1000);
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Fixed-positioned inner section for consistent layout */}
      <div className="bg-secondary fixed inset-0 m-2 flex flex-col items-center justify-center overflow-y-auto rounded-md border p-4 sm:m-4 sm:p-6 md:p-10 lg:m-8">
        <h2 className="mb-3 text-center text-2xl font-bold sm:text-3xl md:text-4xl">
          Contact Us
        </h2>
        <p className="text-muted-foreground mb-10 max-w-2xl text-center text-sm sm:text-base">
          Have questions about our Enterprise plan or need assistance? Fill out
          the form below and we'll get in touch with you shortly.
        </p>

        <div className="w-full max-w-2xl">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  name="name"
                  placeholder="John Doe"
                  value={formData.name}
                  onChange={handleChange}
                  className={cn(errors.name && "border-red-500")}
                />
                {errors.name && (
                  <p className="text-sm text-red-500">{errors.name}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="john.doe@example.com"
                  value={formData.email}
                  onChange={handleChange}
                  className={cn(errors.email && "border-red-500")}
                />
                {errors.email && (
                  <p className="text-sm text-red-500">{errors.email}</p>
                )}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="company">Company Name (Optional)</Label>
              <Input
                id="company"
                name="company"
                placeholder="Acme Inc."
                value={formData.company}
                onChange={handleChange}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="message">Your Message</Label>
              <Textarea
                id="message"
                name="message"
                placeholder="Tell us how we can help..."
                className={cn("min-h-[120px]", errors.message && "border-red-500")}
                value={formData.message}
                onChange={handleChange}
              />
              {errors.message && (
                <p className="text-sm text-red-500">{errors.message}</p>
              )}
            </div>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full md:w-auto"
            >
              {isSubmitting ? "Sending..." : "Submit Message"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ContactUsPage;