import mongoose, { Schema, Document } from 'mongoose';

// ─── User Model ──────────────────────────────────────────────
export interface IUser extends Document {
  user_id: number;
  username?: string;
  first_name?: string;
  created_at: Date;
  premium_posts_added: number;
  premium_expiry?: Date;
  is_banned: boolean;
}

const UserSchema = new Schema<IUser>({
  user_id: { type: Number, required: true, unique: true },
  username: String,
  first_name: String,
  created_at: { type: Date, default: Date.now },
  premium_posts_added: { type: Number, default: 0 },
  premium_expiry: Date,
  is_banned: { type: Boolean, default: false }
}, { collection: 'users' });

export const User = mongoose.models.User || mongoose.model<IUser>('User', UserSchema);

// ─── Post Model ──────────────────────────────────────────────
export interface IPost extends Document {
  id: number; // custom auto-increment or random ID used by the bot
  user_id: number;
  content_type: string;
  content: string;
  caption?: string;
  created_at: Date;
  title?: string;
}

const PostSchema = new Schema<IPost>({
  id: { type: Number, required: true, unique: true },
  user_id: { type: Number, required: true },
  content_type: { type: String, required: true },
  content: { type: String, required: true },
  caption: String,
  created_at: { type: Date, default: Date.now },
  title: String
}, { collection: 'posts' });

export const Post = mongoose.models.Post || mongoose.model<IPost>('Post', PostSchema);

// ─── Project Model (Auto Adders) ─────────────────────────────
export interface IProject extends Document {
  id: number;
  user_id: number;
  channel_id: string;
  channel_title: string;
  buttons_json: string;
  is_active: boolean;
  created_at: Date;
}

const ProjectSchema = new Schema<IProject>({
  id: { type: Number, required: true, unique: true },
  user_id: { type: Number, required: true },
  channel_id: { type: String, required: true },
  channel_title: { type: String, required: true },
  buttons_json: { type: String, required: true },
  is_active: { type: Boolean, default: true },
  created_at: { type: Date, default: Date.now }
}, { collection: 'channel_projects' });

export const Project = mongoose.models.Project || mongoose.model<IProject>('Project', ProjectSchema);
